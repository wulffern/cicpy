######################################################################
##        Copyright (c) 2026 Carsten Wulff Software, Norway
## ###################################################################
##  The MIT License (MIT)
######################################################################

"""Planning groups for cicpy — schematic-driven authoring of layout intent.

A *group* is a named subset of instances within a single cell, used as a
filter when planning placement and routing in the GUI, and (later) consumed
by the pycell to drive `addStack`/`addRoute` calls.

Storage is a sidecar YAML next to the cell's ``.py`` file:

    <cell-dir>/<CellName>.groups.yaml

Membership can be specified three ways and the resolver unions them:

    members:        explicit list of instance names
    member_regex:   list of Python regex patterns matched against names
    member_nets:    list of net names; any instance touching one of these nets
                    is included (resolved against the Cell's SPICE subckt)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Set

import yaml


log = logging.getLogger("cicpy.groups")


@dataclass
class Group:
    name: str
    description: str = ""
    visible: bool = True
    members: List[str] = field(default_factory=list)
    member_regex: List[str] = field(default_factory=list)
    member_nets: List[str] = field(default_factory=list)
    # Phase 4c+ slots — placement and route intent live here. Empty for 4a.
    placement: dict = field(default_factory=dict)
    routes: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "visible": self.visible,
        }
        if self.description:
            d["description"] = self.description
        if self.members:
            d["members"] = list(self.members)
        if self.member_regex:
            d["member_regex"] = list(self.member_regex)
        if self.member_nets:
            d["member_nets"] = list(self.member_nets)
        if self.placement:
            d["placement"] = dict(self.placement)
        if self.routes:
            d["routes"] = list(self.routes)
        return d

    @classmethod
    def from_dict(cls, obj: dict) -> "Group":
        return cls(
            name=str(obj.get("name", "")),
            description=str(obj.get("description", "")),
            visible=bool(obj.get("visible", True)),
            members=list(obj.get("members", []) or []),
            member_regex=list(obj.get("member_regex", []) or []),
            member_nets=list(obj.get("member_nets", []) or []),
            placement=dict(obj.get("placement", {}) or {}),
            routes=list(obj.get("routes", []) or []),
        )

    def add_member(self, name: str) -> None:
        if name and name not in self.members:
            self.members.append(name)

    def remove_member(self, name: str) -> None:
        if name in self.members:
            self.members.remove(name)


@dataclass
class GroupSet:
    cell: str
    groups: List[Group] = field(default_factory=list)
    path: Optional[str] = None  # filesystem path; None until saved

    # ---- I/O ----------------------------------------------------------

    @classmethod
    def empty(cls, cell: str, path: Optional[str] = None) -> "GroupSet":
        return cls(cell=cell, groups=[], path=path)

    @classmethod
    def from_yaml(cls, path: str) -> "GroupSet":
        with open(path) as f:
            obj = yaml.safe_load(f) or {}
        cell = str(obj.get("cell", ""))
        groups = [Group.from_dict(g) for g in (obj.get("groups", []) or [])]
        gs = cls(cell=cell, groups=groups, path=path)
        return gs

    def to_yaml(self, path: Optional[str] = None) -> None:
        target = path or self.path
        if not target:
            raise ValueError("GroupSet.to_yaml: no path supplied")
        obj = {
            "cell": self.cell,
            "groups": [g.to_dict() for g in self.groups],
        }
        with open(target, "w") as f:
            yaml.safe_dump(obj, f, sort_keys=False)
        self.path = target

    # ---- accessors ----------------------------------------------------

    def by_name(self, name: str) -> Optional[Group]:
        for g in self.groups:
            if g.name == name:
                return g
        return None

    def add(self, group: Group) -> None:
        if self.by_name(group.name):
            raise ValueError(f"group already exists: {group.name}")
        self.groups.append(group)

    def remove(self, name: str) -> bool:
        for i, g in enumerate(self.groups):
            if g.name == name:
                del self.groups[i]
                return True
        return False

    # ---- resolver -----------------------------------------------------

    def resolve(
        self,
        all_instance_names: Iterable[str],
        nets_for_instance: Optional[dict] = None,
    ) -> dict:
        """Return {group_name: set(member_instance_names)} for each group.

        ``all_instance_names`` is the universe of candidate instance names
        (typically the cell's top-level instance names). ``nets_for_instance``
        is an optional ``{instance_name: set(net_names)}`` mapping used to
        resolve ``member_nets`` rules; if omitted those rules are skipped.
        """
        out = {}
        all_names = list(all_instance_names)
        nets_for_instance = nets_for_instance or {}

        # Pre-compile regexes
        for g in self.groups:
            members: Set[str] = set()
            for n in g.members:
                if n in all_names:
                    members.add(n)
            for pat in g.member_regex:
                try:
                    rx = re.compile(pat)
                except re.error as exc:
                    log.warning(f"group {g.name!r} regex invalid: {pat!r}: {exc}")
                    continue
                for n in all_names:
                    if rx.search(n):
                        members.add(n)
            if g.member_nets:
                wanted_nets = set(g.member_nets)
                for n in all_names:
                    inst_nets = nets_for_instance.get(n) or set()
                    if inst_nets & wanted_nets:
                        members.add(n)
            out[g.name] = members
        return out

    def visible_members(
        self,
        all_instance_names: Iterable[str],
        nets_for_instance: Optional[dict] = None,
    ) -> Set[str]:
        """Union of members across visible groups. If no groups are visible
        (or no groups exist) returns the empty set; callers should treat that
        as "no filter active"."""
        resolved = self.resolve(all_instance_names, nets_for_instance)
        members: Set[str] = set()
        for g in self.groups:
            if not g.visible:
                continue
            members |= resolved.get(g.name, set())
        return members

    def any_visible(self) -> bool:
        return any(g.visible for g in self.groups)


# ---- path conventions / helpers --------------------------------------

def yaml_path_for(cic_path: str, cell_name: Optional[str] = None) -> str:
    """Derive the sidecar groups.yaml path. Defaults to cellname-based, sitting
    next to the .cic file (which is also where the .py lives by convention)."""
    cic_dir = os.path.dirname(os.path.abspath(cic_path))
    name = cell_name or os.path.splitext(os.path.basename(cic_path))[0]
    return os.path.join(cic_dir, f"{name}.groups.yaml")


def load_or_empty(yaml_path: str, cell_name: str) -> GroupSet:
    if os.path.isfile(yaml_path):
        try:
            gs = GroupSet.from_yaml(yaml_path)
            if not gs.cell:
                gs.cell = cell_name
            return gs
        except Exception as exc:
            log.warning(f"failed to load {yaml_path}: {exc}; starting empty")
    return GroupSet.empty(cell_name, path=yaml_path)


def collect_top_instance_names(cell) -> List[str]:
    """Top-level instance names of a Cell (skips Cuts and ports)."""
    names = []
    for ch in getattr(cell, "children", []) or []:
        if ch is None:
            continue
        if not (hasattr(ch, "isInstance") and ch.isInstance()):
            continue
        if hasattr(ch, "isCut") and ch.isCut():
            continue
        n = getattr(ch, "instanceName", "") or ""
        if n:
            names.append(n)
    return names


def apply(layout, cell_name=None, yaml_path=None, search_dirs=None):
    """Read the sidecar groups YAML for ``cell_name`` and apply each visible
    group's intent to the LayoutCell ``layout``.

    Pycells opt in with one call::

        import cicpy.groups as gp
        gp.apply(layout)                         # uses layout.name
        gp.apply(layout, "LELOTEMP_OTAN")        # explicit cell name
        gp.apply(layout, yaml_path="path/to.yaml")

    Returns ``{group_name: created_object}`` so the caller can wire the
    returned CellGroup / Stack into routing decisions afterwards.

    Honoured schema (Phase 4d minimum):

    .. code-block:: yaml

        groups:
          - name: n_mirr_load
            visible: true
            members: [xn_mirr_load1, xn_mirr_load2]
            placement:
              stack: true
              parent: nmos              # optional CellGroup wrapper
              instances_regex: "^xn_mirr_load"  # overrides members
              order: instanceName       # default; future: 'as_listed'
    """
    if yaml_path is None:
        if cell_name is None:
            cell_name = getattr(layout, "name", "") or ""
        if not cell_name:
            log.warning("apply(): no cell name and no yaml_path; nothing to do")
            return {}
        candidates = []
        layout_dir = getattr(layout, "dirname", None)
        if layout_dir:
            candidates.append(os.path.join(layout_dir, f"{cell_name}.groups.yaml"))
        for d in (search_dirs or []):
            candidates.append(os.path.join(d, f"{cell_name}.groups.yaml"))
        candidates.append(os.path.join(os.getcwd(), f"{cell_name}.groups.yaml"))
        yaml_path = next((p for p in candidates if os.path.isfile(p)), None)
        if yaml_path is None:
            log.info(
                f"apply({cell_name}): no sidecar YAML found "
                f"(looked at {len(candidates)} locations)"
            )
            return {}

    gs = GroupSet.from_yaml(yaml_path)
    out: dict = {}
    cellgroups: dict = {}

    for g in gs.groups:
        if not g.visible:
            continue
        place = g.placement or {}
        if not place.get("stack"):
            continue

        parent_name = place.get("parent", "") or g.name
        cg = cellgroups.get(parent_name)
        if cg is None:
            try:
                cg = layout.makeCellGroup(parent_name)
            except Exception as exc:
                log.warning(f"apply: makeCellGroup({parent_name!r}) failed: {exc}")
                continue
            cellgroups[parent_name] = cg

        regex = place.get("instances_regex")
        if not regex:
            if g.member_regex:
                regex = "|".join(g.member_regex)
            elif g.members:
                regex = "^(" + "|".join(re.escape(m) for m in g.members) + ")$"

        if not regex:
            log.info(f"apply: group {g.name!r} has no resolvable members; skipping")
            continue

        try:
            instances = layout.getSortedInstancesByInstanceName(regex)
        except Exception as exc:
            log.warning(f"apply: regex {regex!r} matched no instances: {exc}")
            continue

        try:
            stack = cg.addStack(g.name, instances)
        except Exception as exc:
            log.warning(f"apply: addStack({g.name!r}) failed: {exc}")
            continue
        out[g.name] = stack
        log.info(
            f"apply: group {g.name!r} → stack of {len(instances)} instances "
            f"in CellGroup {parent_name!r}"
        )

    # ---- routes ----
    for g in gs.groups:
        if not g.visible:
            continue
        for r in (g.routes or []):
            try:
                _apply_route(layout, cellgroups, r)
            except Exception as exc:
                log.warning(f"apply route {r!r} failed: {exc}")

    return out


def _apply_route(layout, cellgroups, r):
    """Emit one route. Honoured kinds: ``connection`` (LayoutCell.addRouteConnection)
    and ``orthogonal`` (addOrthogonalConnectivityRoute on a CellGroup or the layout)."""
    kind = (r.get("kind") or "connection").lower()
    net = r.get("net", "")
    if not net:
        return
    pattern = r.get("net_regex") or f"^{re.escape(net)}$"

    if kind == "connection":
        layout.addRouteConnection(
            pattern,
            r.get("include_instances", "") or "",
            r.get("layer", "M1") or "M1",
            r.get("location", "") or "",
            r.get("options", "") or "",
            r.get("route_type", "") or "",
        )
        log.info(f"apply: connection route net={net} layer={r.get('layer')}")
        return

    if kind == "orthogonal":
        parent = r.get("parent", "") or ""
        target = None
        if parent:
            target = cellgroups.get(parent)
            if target is None:
                target = layout.makeCellGroup(parent)
                cellgroups[parent] = target
        if target is not None:
            # CellGroup variant — no includeInstances arg
            target.addOrthogonalConnectivityRoute(
                r.get("layer1", "M2") or "M2",
                r.get("layer2", "M3") or "M3",
                pattern,
                r.get("options", "") or "",
                int(r.get("cuts", 1) or 1),
                r.get("exclude_instances", "") or "",
                accessLayer=r.get("access_layer") or None,
            )
        else:
            # Layout-level variant
            layout.addOrthogonalConnectivityRoute(
                r.get("layer1", "M2") or "M2",
                r.get("layer2", "M3") or "M3",
                pattern,
                r.get("options", "") or "",
                int(r.get("cuts", 1) or 1),
                r.get("exclude_instances", "") or "",
                r.get("include_instances", "") or "",
                accessLayer=r.get("access_layer") or None,
            )
        log.info(f"apply: orthogonal route net={net} {r.get('layer1')}/{r.get('layer2')}")
        return

    log.warning(f"apply: unknown route kind {kind!r} for net {net!r}")


def collect_instance_nets(cell) -> dict:
    """Return {instance_name: set(net_names)} from the cell's SPICE subckt.

    Best-effort: returns an empty dict if the cell has no ``ckt`` attribute
    or its subckt doesn't expose instances. The viewer can still resolve
    explicit ``members`` and ``member_regex`` rules without this mapping.
    """
    out: dict = {}
    ckt = getattr(cell, "ckt", None)
    if ckt is None:
        return out
    insts = getattr(ckt, "instances", None) or getattr(ckt, "subInstances", None)
    if insts is None:
        return out
    try:
        iterable = insts.values() if hasattr(insts, "values") else list(insts)
    except Exception:
        return out
    for inst in iterable:
        name = getattr(inst, "name", "") or ""
        nodes = getattr(inst, "nodes", None) or []
        if name and nodes:
            out[name] = set(str(n) for n in nodes)
    return out
