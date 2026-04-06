#!/opt/eda/python3/bin//python3
import gzip
import json
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "..", "src"))
TECH = os.path.normpath(os.path.join(HERE, "..", "transpile", "demo.tech"))
SOURCE_CIC = os.path.normpath(os.path.join(HERE, "..", "transpile", "SAR9B_CV.cic.gz"))
SOURCE_SPI = os.path.join(HERE, "route_examples.spi")
OUT_CIC = os.path.join(HERE, "route_examples.cic.gz")

sys.path.insert(0, SRC)

import cicpy as cic
import cicspi as spi

LABEL_DY = 1200
XSPACE = 0
YSPACE = 0

DEMO_CONFIGS = [
    {
        "name": "ROUTE_STRAIGHT",
        "routes": [("connectivity", ("M3", r"^G$", "-", "nolabel,routeWidth=minwidth", 1, "", ""))],
        "labels": [("xleft0", "G", "A"), ("xright0", "G", "B")],
    },
    {
        "name": "ROUTE_STRAIGHT_WITH_CUTS",
        "routes": [("connectivity", ("M3", r"^D$", "-", "nolabel,routeWidth=minwidth,fillvcut,startoffsetcuthigh,endoffsetcutlow", 1, "", ""))],
        "labels": [("xleft0", "D", "A"), ("xright0", "D", "B")],
    },
    {
        "name": "ROUTE_STRAIGHT_WITH_FILLHCUT",
        "routes": [("connectivity", ("M3", r"^G$", "-", "nolabel,routeWidth=minwidth,fillhcut", 1, "", ""))],
        "labels": [("xleft0", "G", "A"), ("xright0", "G", "B")],
    },
    {
        "name": "ROUTE_LEFT",
        "routes": [("connectivity", ("M2", r"^D$", "-|--", "nolabel,routeWidth=minwidth", 1, "", ""))],
        "labels": [("xleft0", "D", "A1"), ("xleft1", "D", "A2"), ("xright0", "D", "B")],
    },
    {
        "name": "ROUTE_RIGHT",
        "routes": [("connectivity", ("M2", r"^S$", "--|-", "nolabel,routeWidth=minwidth", 1, "", ""))],
        "labels": [("xleft0", "S", "A"), ("xright0", "S", "B1"), ("xright1", "S", "B2")],
    },
    {
        "name": "ROUTE_VERTICAL",
        "routes": [("connectivity", ("M2", r"^D$", "||", "nolabel,routeWidth=minwidth", 1, "", ""))],
        "labels": [("xcol0", "D", "A"), ("xcol1", "D", "B")],
    },
    {
        "name": "ROUTE_VERTICAL_ANTENNA",
        "routes": [("connectivity", ("M2", r"^D$", "||", "nolabel,routeWidth=minwidth,antenna", 1, "", ""))],
        "labels": [("xcol0", "D", "A"), ("xcol3", "D", "B")],
    },
    {
        "name": "ROUTE_U_LEFT",
        "routes": [("connectivity", ("M2", r"^D$", "|-", "nolabel,routeWidth=minwidth,track1", 1, "", ""))],
        "labels": [("xcol0", "D", "A"), ("xcol1", "D", "B")],
    },
    {
        "name": "ROUTE_U_RIGHT",
        "routes": [("connectivity", ("M2", r"^D$", "-|", "nolabel,routeWidth=minwidth,track1", 1, "", ""))],
        "labels": [("xcol0", "D", "A"), ("xcol1", "D", "B")],
    },
    {
        "name": "ROUTE_U_TOP",
        "routes": [("connectivity", ("M3", r"^G$", "--|", "nolabel,routeWidth=minwidth,track1", 1, "", ""))],
        "labels": [("xleft0", "G", "A"), ("xright0", "G", "B")],
    },
    {
        "name": "ROUTE_U_BOTTOM",
        "routes": [("connectivity", ("M3", r"^G$", "|--", "nolabel,routeWidth=minwidth,track1", 1, "", ""))],
        "labels": [("xleft0", "G", "A"), ("xright0", "G", "B")],
    },
    {
        "name": "ROUTE_LEFT_DOWN_LEFT_UP",
        "routes": [("connectivity", ("M3", r"^G$", "-|--", "nolabel,routeWidth=minwidth,leftdownleftup", 1, "", ""))],
        "labels": [("xleft0", "G", "A1"), ("xleft1", "G", "A2"), ("xright0", "G", "B1"), ("xright1", "G", "B2")],
    },
    {
        "name": "ROUTE_LULD",
        "routes": [("connectivity", ("M3", r"^G$", "-|--", "nolabel,routeWidth=minwidth,leftupleftdown", 1, "", ""))],
        "labels": [("xleft0", "G", "A1"), ("xleft1", "G", "A2"), ("xright0", "G", "B1"), ("xright1", "G", "B2")],
    },
    {
        "name": "ROUTE_STRAP_HORIZONTAL",
        "routes": [("connectivity", ("M3", r"^G$", "-", "nolabel,routeWidth=minwidth,strap", 1, "", ""))],
        "labels": [("xleft0", "G", "A"), ("xright0", "G", "B1"), ("xright1", "G", "B2")],
    },
    {
        "name": "ROUTE_STRAP_VERTICAL",
        "routes": [("connectivity", ("M2", r"^D$", "||", "nolabel,routeWidth=minwidth,strap,vertical", 1, "", ""))],
        "labels": [("xsrc0", "D", "A"), ("xmid0", "D", "B1"), ("xright0", "D", "B2")],
    },
    {
        "name": "ROUTE_ORTHOGONAL",
        "routes": [("orthogonal", ("M2", "M3", r"^D$", "nolabel,routeWidth=minwidth", 1, "", "", "M1"))],
        "labels": [("xleft0", "D", "A1"), ("xmid0", "D", "A2"), ("xright0", "D", "A3")],
    },
]


def load_base_design():
    base = cic.Design()
    base.fromJsonFile(SOURCE_CIC)
    return base


def parse_spice():
    sp = spi.SpiceParser()
    sp.parseFile(SOURCE_SPI)


def make_design(base):
    design = cic.Design()
    design.getLayoutCell = types.MethodType(lambda self, name: self.getCell(name), design)
    nchdl = base.getCell("NCHDL")
    nchdl.design = design
    design.add(nchdl)
    return design


def make_layoutcell(design, subckt_name):
    ckt = spi.Subckt.getSubckt(subckt_name)
    cell = cic.LayoutCell()
    cell.name = subckt_name
    cell.ckt = ckt
    cell.subckt = ckt
    cell.parent = design
    cell.design = design
    cell.place_xspace = [XSPACE]
    cell.place_yspace = [YSPACE]
    cell.place_groupbreak = [100]
    design.add(cell)
    cell.place()
    return cell


def add_terminal_labels(cell, labels):
    instances = {child.instanceName: child for child in cell.children if child.isInstance()}
    for instance_name, terminal_name, text_value in labels:
        inst = instances.get(instance_name)
        if inst is None:
            continue
        access = inst.getTerminalAccess(terminal_name, target_layer="M1")
        if access is None or access.isEmpty():
            continue
        rect = access.primary()
        text = cic.Text(text_value)
        text.moveTo(rect.x1, rect.y2 + LABEL_DY)
        cell.add(text)


def route_cell(cell, route_specs):
    for method, args in route_specs:
        if method == "connectivity":
            cell.addConnectivityRoute(*args)
        elif method == "orthogonal":
            cell.addOrthogonalConnectivityRoute(*args)
        else:
            raise ValueError(method)

    for child in list(cell.children):
        if child.isRoute():
            child.route()


def collect_cut_cells(obj, design, seen=None):
    if seen is None:
        seen = set()
    for child in getattr(obj, "children", []):
        cut_cell = getattr(child, "_cell_obj", None)
        if cut_cell is not None and cut_cell.name not in seen:
            cut_cell.design = design
            design.add(cut_cell)
            seen.add(cut_cell.name)
        if getattr(child, "children", None):
            collect_cut_cells(child, design, seen)
    return seen




def reorder_design_cells(design):
    ordered = []
    cuts = [name for name in design.cellnames if name.startswith("cut_")]
    base = [name for name in design.cellnames if name == "NCHDL"]
    demos = [name for name in design.cellnames if name not in cuts and name != "NCHDL"]
    ordered.extend(cuts)
    ordered.extend(base)
    ordered.extend(demos)
    design.cellnames = ordered

def main():
    cic.Rules(TECH)
    parse_spice()
    base = load_base_design()
    design = make_design(base)

    for cfg in DEMO_CONFIGS:
        cell = make_layoutcell(design, cfg["name"])
        add_terminal_labels(cell, cfg["labels"])
        route_cell(cell, cfg["routes"])
        collect_cut_cells(cell, design)
        cell.updateBoundingRect()

    reorder_design_cells(design)

    with gzip.open(OUT_CIC, "wt") as fo:
        json.dump(design.toJson(), fo, indent=2)

    svg = cic.SvgPrinter("ROUTE_DEMOS", cic.Rules.getInstance(), 10, 100, 100)
    svg.print(design)


if __name__ == "__main__":
    main()
