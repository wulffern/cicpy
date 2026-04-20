import hashlib
import logging
import os
import re
import subprocess

import cicpy as cic
from cicpy.eda.magicdesign import MagicFile


class PrimitiveLayoutProvider:
    def __init__(self, techlib):
        self.techlib = techlib
        self.log = logging.getLogger(self.__class__.__name__)

    def supports(self, design, subckt_name):
        return False

    def canonical_port_order(self, subckt_name):
        return []

    def generate(self, design, subckt_name, instance):
        return None


class Sky130MagicPrimitiveProvider(PrimitiveLayoutProvider):
    SUPPORTED_PORTS = {
        "sky130_fd_pr__pfet_01v8": ["D", "G", "S", "B"],
        "sky130_fd_pr__nfet_01v8": ["D", "G", "S", "B"],
        "sky130_fd_pr__pfet_01v8_lvt": ["D", "G", "S", "B"],
        "sky130_fd_pr__nfet_01v8_lvt": ["D", "G", "S", "B"],
        "sky130_fd_pr__pfet_01v8_hvt": ["D", "G", "S", "B"],
        "sky130_fd_pr__nfet_01v8_hvt": ["D", "G", "S", "B"],
    }

    def __init__(self, techlib):
        super().__init__(techlib)
        self.magic_rc = f"/opt/pdk/share/pdk/{techlib}/libs.tech/magic/{techlib}.magicrc"
        self.magic_tcl = f"/opt/pdk/share/pdk/{techlib}/libs.tech/magic/{techlib}.tcl"
        self.magic_namespace = techlib.replace("A", "").replace("B", "")

    def supports(self, design, subckt_name):
        return subckt_name in self.SUPPORTED_PORTS and os.path.exists(self.magic_rc)

    def canonical_port_order(self, subckt_name):
        return list(self.SUPPORTED_PORTS.get(subckt_name, []))

    def _sanitize_value(self, value):
        vv = str(value).strip().strip("'").strip('"')
        vv = vv.replace(".", "p").replace("-", "m")
        vv = re.sub(r"[^A-Za-z0-9_]+", "_", vv)
        return vv

    def _cell_name(self, subckt_name, instance):
        params = []
        for key in ("W", "L", "nf", "m"):
            if instance.hasProperty(key):
                params.append(f"{key.lower()}_{self._sanitize_value(instance.getPropertyString(key))}")
        if not params:
            digest = hashlib.sha1(instance.spiceStr.encode("utf-8")).hexdigest()[:10]
            params.append(digest)
        return f"{subckt_name}__{'__'.join(params)}"

    def _cache_dir(self, design):
        base = getattr(design, "primitive_cache_dir", "")
        if not base:
            return ""
        os.makedirs(base, exist_ok=True)
        return base

    def _collect_params(self, instance):
        out = []
        for key in ("W", "L", "m", "nf"):
            if instance.hasProperty(key):
                out.extend([key.lower(), instance.getPropertyString(key).strip("'").strip('"')])
        if "nf" not in [out[i] for i in range(0, len(out), 2)]:
            out.extend(["nf", "1"])
        if "m" not in [out[i] for i in range(0, len(out), 2)]:
            out.extend(["m", "1"])
        return out

    def _infer_terminal_ports(self, layout_cell):
        metal1 = []
        locali = []
        for child in layout_cell.children:
            if child is None or not child.isRect():
                continue
            if child.layer == "M1":
                metal1.append(child.getCopy())
            elif child.layer == "LI":
                locali.append(child.getCopy())

        if not metal1:
            return

        metal1.sort(key=lambda r: (r.centerX(), r.centerY()))
        left = min(metal1, key=lambda r: (r.centerX(), r.centerY()))
        right = max(metal1, key=lambda r: (r.centerX(), r.centerY()))
        center = min(metal1, key=lambda r: abs(r.centerX() - layout_cell.centerX()) + abs(r.centerY() - layout_cell.centerY()))

        if "D" not in layout_cell.ports:
            layout_cell.updatePort("D", left.getCopy("M1"), routeLayer="M1")
        if "S" not in layout_cell.ports:
            layout_cell.updatePort("S", right.getCopy("M1"), routeLayer="M1")
        if "G" not in layout_cell.ports:
            layout_cell.updatePort("G", center.getCopy("M1"), routeLayer="M1")

        if locali and "B" not in layout_cell.ports:
            bulk = max(locali, key=lambda r: (r.width() * r.height(), abs(r.centerX() - layout_cell.centerX())))
            layout_cell.updatePort("B", bulk.getCopy("LI"), routeLayer="LI")

    def generate(self, design, subckt_name, instance):
        cache_dir = self._cache_dir(design)
        if cache_dir == "":
            return None

        cell_name = self._cell_name(subckt_name, instance)
        mag_path = os.path.join(cache_dir, cell_name + ".mag")
        if not os.path.exists(mag_path):
            params = self._collect_params(instance)
            tcl_lines = [
                f"crashbackups stop",
                f"load {cell_name} -silent",
                f"magic::gencell {self.magic_namespace}::{subckt_name} {cell_name} -spice {' '.join(params)}",
                "save",
                "quit -noprompt",
            ]
            self.log.info(f"Generating primitive layout {cell_name} for {subckt_name}")
            subprocess.run(
                ["magic", "-noconsole", "-dnull", "-rcfile", self.magic_rc],
                input="\n".join(tcl_lines) + "\n",
                text=True,
                cwd=cache_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        mf = MagicFile(mag_path, design)
        design.maglib[cell_name] = mf
        layout_cell = mf.getLayoutCell()
        if layout_cell is not None:
            layout_cell.name = cell_name
            layout_cell.parent = design
            layout_cell.libpath = cache_dir
            self._infer_terminal_ports(layout_cell)
        return layout_cell


def register_default_providers(design):
    techlib = getattr(design, "techlib", "")
    if not techlib.startswith("sky130"):
        return
    design.registerPrimitiveProvider(Sky130MagicPrimitiveProvider(techlib))
