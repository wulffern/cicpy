######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

import glob
import logging
import os
import sys

import yaml


log = logging.getLogger("cicpy.gui")


def discover_libraries(cicfile):
    """Auto-discover sibling library .cic files via the IP's config.yaml.

    Walks up from cicfile to find the first config.yaml. Its top-level keys
    that look like cicconf dependency entries (have ``remote`` or ``revision``)
    are treated as dependency names; for each, ``<workspace>/<dep>/design/*.cic``
    is included. Returns a sorted list, excluding cicfile itself.
    """
    cicfile = os.path.abspath(cicfile)
    d = os.path.dirname(cicfile)
    ip_config = None
    ip_root = None
    while d and d != "/":
        cfg = os.path.join(d, "config.yaml")
        if os.path.isfile(cfg):
            ip_config = cfg
            ip_root = d
            break
        d = os.path.dirname(d)
    if ip_config is None:
        return []
    workspace = os.path.dirname(ip_root)
    try:
        with open(ip_config) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as exc:
        log.warning(f"Could not read {ip_config}: {exc}")
        return []
    libs = []
    for name, val in cfg.items():
        if not isinstance(val, dict):
            continue
        if "remote" not in val and "revision" not in val:
            continue
        dep_design = os.path.join(workspace, name, "design")
        if not os.path.isdir(dep_design):
            continue
        for path in sorted(glob.glob(os.path.join(dep_design, "*.cic"))):
            if os.path.abspath(path) == cicfile:
                continue
            libs.append(path)
    return libs


def discover_tech(cicfile):
    """Walk up from cicfile to find a tech/cic/*.tech file, mirroring the
    layout convention used by spi2mag (../tech/cic/<techlib>.tech)."""
    d = os.path.dirname(os.path.abspath(cicfile))
    while d and d != "/":
        for sub in ("tech/cic", "tech"):
            tdir = os.path.join(d, sub)
            if os.path.isdir(tdir):
                hits = sorted(glob.glob(os.path.join(tdir, "*.tech")))
                if hits:
                    return hits[0]
        d = os.path.dirname(d)
    return None


def run(cicfile, techfile=None, includes=(), auto_libs=True,
        rerun_cmd=None, rerun_cwd=None):
    if techfile is None:
        techfile = discover_tech(cicfile)
        if techfile is None:
            raise SystemExit(
                "No --tech provided and could not find tech/cic/*.tech "
                f"by walking up from {cicfile}."
            )

    final_includes = list(includes or [])
    auto = []
    if auto_libs:
        auto.extend(discover_libraries(cicfile))
    if auto:
        existing = {os.path.abspath(p) for p in final_includes}
        for path in auto:
            if os.path.abspath(path) not in existing:
                final_includes.append(path)
        log.info(f"auto-discovered {len(auto)} libraries:")
        for p in auto:
            log.info(f"  - {p}")

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        raise SystemExit(
            "PySide6 is not installed. Install with: pip install 'cicpy[gui]'"
        )

    from .mainwindow import MainWindow

    app = QApplication.instance()
    owns_app = app is None
    if owns_app:
        app = QApplication(sys.argv)
        app.setOrganizationName("cicpy")
        app.setApplicationName("gui")

    win = MainWindow(
        cicfile, techfile, includes=final_includes,
        rerun_cmd=rerun_cmd, rerun_cwd=rerun_cwd,
    )
    win.show()

    if owns_app:
        sys.exit(app.exec())
