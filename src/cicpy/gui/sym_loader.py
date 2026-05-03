######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

import logging
import os

import yaml

from cicpy.eda.xschem import Symbol


log = logging.getLogger("cicpy.gui.sym_loader")


# Hardcoded last-resort probe paths for the xschem standard library
# (where devices/ipin.sym lives). Used only if XSCHEM_LIBRARY_PATH is unset.
_XSCHEM_FALLBACK_DIRS = [
    "/usr/local/share/xschem/xschem_library",
    "/opt/homebrew/share/xschem/xschem_library",
    os.path.expanduser("~/.xschem/xschem_library"),
    os.path.expanduser("~/data/2023/aicex/tests/xschem/xschem_library"),
]


def _ip_config_root(start_dir):
    d = start_dir
    while d and d != "/":
        cfg = os.path.join(d, "config.yaml")
        if os.path.isfile(cfg):
            return d, cfg
        d = os.path.dirname(d)
    return None, None


def _add_symbol_lib_paths(paths, symbol_libs=None, techfile=None, anchor=None):
    if not symbol_libs:
        return
    if isinstance(symbol_libs, str):
        symbol_libs = [symbol_libs]

    bases = [os.getcwd()]
    if anchor:
        anchor_dir = os.path.dirname(os.path.abspath(anchor))
        bases.append(anchor_dir)
        ip_root, _ = _ip_config_root(anchor_dir)
        if ip_root:
            bases.append(ip_root)
            bases.append(os.path.join(ip_root, "work"))
    if techfile:
        bases.append(os.path.dirname(os.path.abspath(techfile)))

    for raw in symbol_libs:
        if not raw:
            continue
        expanded = os.path.expanduser(os.path.expandvars(str(raw)))
        candidates = [expanded] if os.path.isabs(expanded) else [
            os.path.normpath(os.path.join(base, expanded)) for base in bases
        ]
        for cand in candidates:
            if os.path.isdir(cand):
                paths.append(cand)
                parent = os.path.dirname(cand)
                if parent and os.path.isdir(parent):
                    paths.append(parent)
                break


def discover_symbol_paths(schfile=None, cicfile=None, techfile=None, symbol_libs=None):
    """Build an ordered, de-duplicated list of search directories for .sym files."""
    paths = []

    env = os.environ.get("XSCHEM_LIBRARY_PATH")
    if env:
        for p in env.split(os.pathsep):
            if p:
                paths.append(p)

    # Walk up from the schematic file. Symref strings are relative to one of
    # these directories.
    anchor = schfile or cicfile
    if anchor:
        d = os.path.dirname(os.path.abspath(anchor))
        for _ in range(6):
            if d and os.path.isdir(d):
                paths.append(d)
            new_d = os.path.dirname(d)
            if new_d == d:
                break
            d = new_d

    _add_symbol_lib_paths(paths, symbol_libs, techfile, anchor)

    # Workspace dependency design dirs, via the IP's config.yaml
    if anchor:
        ip_root, ip_cfg = _ip_config_root(os.path.dirname(os.path.abspath(anchor)))
        if ip_cfg is not None:
            workspace = os.path.dirname(ip_root)
            try:
                with open(ip_cfg) as f:
                    cfg = yaml.safe_load(f) or {}
            except Exception as exc:
                log.warning(f"Could not read {ip_cfg}: {exc}")
                cfg = {}
            for name, val in cfg.items():
                if not isinstance(val, dict):
                    continue
                if "remote" not in val and "revision" not in val:
                    continue
                dep_design = os.path.join(workspace, name, "design")
                if os.path.isdir(dep_design):
                    paths.append(dep_design)
            # Also the IP's own design dir (covers self-references)
            own_design = os.path.join(ip_root, "design")
            if os.path.isdir(own_design):
                paths.append(own_design)

    # cicpy's packaged xschem/ directory (cic primitive symbols)
    try:
        import cicpy
        cicpy_dir = os.path.dirname(os.path.abspath(cicpy.__file__))
        cicpy_xschem = os.path.normpath(os.path.join(cicpy_dir, "..", "..", "xschem"))
        if os.path.isdir(cicpy_xschem):
            paths.append(cicpy_xschem)
    except Exception:
        pass

    # XSchem standard library fallbacks
    for c in _XSCHEM_FALLBACK_DIRS:
        if os.path.isdir(c):
            paths.append(c)

    # Dedup while preserving order
    seen = set()
    out = []
    for p in paths:
        ap = os.path.abspath(p)
        if ap in seen:
            continue
        seen.add(ap)
        out.append(ap)
    return out


class SymbolLoader:
    """Resolves XSchem symref strings to absolute paths and parses Symbol objects with caching."""

    def __init__(self, search_paths=None):
        self.search_paths = list(search_paths or [])
        self._cache = {}
        self._missing = set()

    def add_path(self, path):
        if path and os.path.isdir(path):
            ap = os.path.abspath(path)
            if ap not in self.search_paths:
                self.search_paths.append(ap)

    def resolve(self, symref):
        if not symref:
            return None
        if os.path.isabs(symref) and os.path.isfile(symref):
            return os.path.abspath(symref)
        for d in self.search_paths:
            cand = os.path.join(d, symref)
            if os.path.isfile(cand):
                return os.path.abspath(cand)
        return None

    def load(self, symref):
        path = self.resolve(symref)
        if path is None:
            if symref not in self._missing:
                self._missing.add(symref)
                log.warning(f"symbol not found: {symref}")
            return None
        if path in self._cache:
            return self._cache[path]
        try:
            sym = Symbol.fromFile(path)
        except Exception as exc:
            log.warning(f"failed to parse {path}: {exc}")
            return None
        self._cache[path] = sym
        return sym
