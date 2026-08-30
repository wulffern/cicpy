#!/usr/bin/env python3
"""Run the whole parity corpus: compile every design with ciccreator
AND cicpy on identical inputs, compare shape for shape, and fail on
any regression.

The corpus repositories are cloned next to this file by cicconf:

    cd tests/parity
    cicconf --config config.yaml clone --https
    python3 run_corpus.py

The reference is compiled from source if `bin/linux/cic` is missing
(qmake6 + make over cic-core and cic only -- the GUI is not needed).

The expectation is EXACT parity everywhere, with one recorded
exception: TEST_R in routes.json differs by one database unit because
of ciccreator's integer rotate(90) -- a bug in the reference that
cicpy deliberately does not replicate.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compare_cic

#- (name, repo, workdir, ref args, cicpy args) -- args are argv lists
#- relative to workdir; {CIC} is the reference binary.
def _repo(name, repo, tech):
    args = ["--I", "../cic", "../cic/ip.json", "../cic/" + tech]
    return (name, repo, "work", args + ["ref_" + name],
            args + ["cicpy_" + name])

CORPUS = [
    ("routes", "ciccreator", ".",
     ["examples/routes.json", "examples/tech.json", "ref_routes"],
     ["examples/routes.json", "examples/tech.json", "cicpy_routes"]),
    ("SAR_ESSCIRC16_28N", "ciccreator", ".",
     ["examples/SAR_ESSCIRC16_28N.json", "examples/tech.json", "ref_SAR"],
     ["examples/SAR_ESSCIRC16_28N.json", "examples/tech.json", "cicpy_SAR"]),
    _repo("JNW_TR", "jnw_tr_sky130a", "sky130.tech"),
    _repo("JNW_ATR", "jnw_atr_sky130a", "sky130.tech"),
    _repo("REY_TR", "rey_tr_sky130a", "sky130.tech"),
    _repo("REY_ATR", "rey_atr_sky130a", "sky130.tech"),
    _repo("LELO_ATR", "lelo_atr_sky130a", "sky130.tech"),
    _repo("LELO_TR_IHP", "lelo_tr_ihp13g2", "ihp-sg13g2.tech"),
    _repo("LELO_ATR_IHP", "lelo_atr_ihp13g2", "ihp-sg13g2.tech"),
    _repo("CNR_ATR", "cnr_atr_sky130nm", "sky130.tech"),
    _repo("SUN_TR", "sun_tr_sky130nm", "sky130.tech"),
    _repo("SUN_SAR9B", "sun_sar9b_sky130nm", "sky130.tech"),
    _repo("SUN_PLL", "sun_pll_sky130nm", "sky130.tech"),
]

#- cells allowed to differ, per design
ALLOWED = {
    "routes": {"TEST_R"},
}


def build_reference(root):
    cic = os.path.join(root, "bin", "linux", "cic")
    if os.path.exists(cic):
        return cic
    print("== building ciccreator (cic-core + cic)")
    #- the top-level `make compile` generates version.h before qmake;
    #- building the sub-projects directly must do the same or main.cpp
    #- dies on the include
    ver = os.path.join(root, "cic", "src", "version.h")
    if not os.path.exists(ver):
        with open(ver, "w") as f:
            f.write('#define CICVERSION "parity-corpus"\n'
                    '#define CICHASH "parity-corpus"\n')
    for sub in ("cic-core", "cic"):
        d = os.path.join(root, sub)
        subprocess.run(["qmake6", "DEFINES+=QMAKE_6"], cwd=d, check=True)
        subprocess.run(["make", "-j2"], cwd=d, check=True)
    if not os.path.exists(cic):
        raise SystemExit("ciccreator build produced no " + cic)
    return cic


def run(argv, cwd):
    r = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    return r.returncode, r.stdout


def compare(ref, cand, allowed):
    a = compare_cic.index(compare_cic.load(ref))
    b = compare_cic.index(compare_cic.load(cand))
    bad = []
    for name in sorted(set(a) | set(b)):
        if name in allowed:
            continue
        if a.get(name) != b.get(name):
            bad.append(name)
    return bad, len(set(a) | set(b))


def main():
    corpus_dir = os.environ.get("PARITY_CORPUS", HERE)
    cicpy = os.environ.get("PARITY_CICPY", "cicpy")
    cic = build_reference(os.path.join(corpus_dir, "ciccreator"))

    failures = []
    for name, repo, workdir, ref_args, cand_args in CORPUS:
        cwd = os.path.join(corpus_dir, repo, workdir)
        if not os.path.isdir(cwd):
            failures.append((name, "repo not cloned: " + cwd))
            print("%-18s MISSING %s" % (name, cwd))
            continue

        rc, out = run([cic] + ref_args, cwd)
        if rc != 0:
            failures.append((name, "reference compile failed\n" + out[-2000:]))
            print("%-18s REF FAILED" % name)
            continue
        rc, out = run([cicpy, "compile"] + cand_args, cwd)
        if rc != 0:
            failures.append((name, "cicpy compile failed\n" + out[-2000:]))
            print("%-18s CICPY FAILED" % name)
            continue

        ref_cic = os.path.join(cwd, ref_args[-1] + ".cic")
        cand_cic = os.path.join(cwd, cand_args[-1] + ".cic")
        allowed = ALLOWED.get(name, set())
        bad, total = compare(ref_cic, cand_cic, allowed)
        if bad:
            failures.append((name, "cells differ: " + ", ".join(bad)))
            print("%-18s %d/%d  DIFFERS: %s"
                  % (name, total - len(bad), total, ", ".join(bad)))
        else:
            note = " (allowed: %s)" % ", ".join(sorted(allowed)) if allowed else ""
            print("%-18s %d/%d  OK%s" % (name, total - len(allowed), total, note))

    if failures:
        print("\nPARITY REGRESSION in %d design(s):" % len(failures))
        for name, why in failures:
            print("  %s: %s" % (name, why))
        return 1
    print("\nPARITY: the whole corpus matches the reference")
    return 0


if __name__ == "__main__":
    sys.exit(main())
