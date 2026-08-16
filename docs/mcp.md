---
layout: default
title: MCP server
nav_order: 4
---

# MCP server

`cicpy` ships an [MCP](https://modelcontextprotocol.io) server so an
agent doing schematic-driven layout can *look before it draws*: render
a cell or a finished GDS as an inline image, inspect placement and
connectivity, measure what blocks a lane, and run the design
repository's own checks — without a rebuild per question.

## Install and run

```bash
pip install cicpy[mcp]     # the server framework + render deps
cicpy-mcp                  # run directly, or point a client at it
```

An MCP client config entry:

```json
{ "cicpy": { "command": "cicpy-mcp" } }
```

cicpy is technology independent and so is the server: the technology
file is always an argument, and DRC runs through the repository's own
`make drc`, so the rules and tools stay where the repository put them.

## The tools

Ask-before-you-draw — each of these answers without a regeneration:

| tool | question it answers |
|---|---|
| `layout_guide` | the [field guide](/cicpy/agent_layout) itself — read it first |
| `render` | draw a cell from a `.cic`, returned inline, y up |
| `render_gds` | draw a finished GDS the way a layout engineer reads it; `top_only` leaves placed blocks as outlines |
| `cell_info` | placement in a `.cic`: instances, groups, pitches, ports |
| `netlist_info` | which devices connect to which nets — read before choosing placement groups |
| `stackorder` | which columns are interleaved on a terminal, and what reordering buys |
| `tracks` | which routing tracks are occupied, and by what; `free` reports usable spans |
| `blockers` | what stops a net dropping a via column in a box — the via-COLUMN check no same-layer scan can do |
| `findroute` | search a path for a net and report it **without drawing** |
| `route_options` | what each routing option means, and which ones lie to you |
| `checkroutes` | shorts and opens in a built `.cic`, with BRIDGE/CHAIN attribution |
| `connectivity` | rerun the repo's sch2mag with the connectivity check — the same analysis the GUI shows |
| `drc` | run the repository's own `make drc` and report the rules that fired |

The routing loop these serve is the one in the
[field guide](/cicpy/agent_layout): measure (`tracks`, `blockers`,
`netlist_info`) → search (`findroute`, or a declared maze) → import
the emitted story into the sidecar → verify (`drc`, `checkroutes`,
plus the repo's kdrc/lvs/ant targets) → next net.

Two habits that pay:

- **`blockers` before believing a clean track report.** A trunk on M4
  and a pin on M1 never share a track; what collides is the via
  column. Every routing failure measured so far was this.
- **`checkroutes` is blind to raw contact paint** (paint-stitched
  supply straps): for those, magic extraction and LVS are the truth.
