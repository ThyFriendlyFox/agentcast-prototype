# STATUS.md — where the project actually stands

The single source of truth for project state. Claims require evidence: a
passing gate, a linked run, a tag. Updated in the same commit as the
behavior change. The weekly cycle (WEEKLY.md step 5) refreshes it.

| Area | State | Evidence |
|---|---|---|
| v0.4 male HDMI plug | ✅ | `workcenter gates` GREEN on `hardware/v0.4/dongle`; `render --strict` passes |
| v0.4 plug footprint confirmed | ❌ | needs the XUNPU HDMI-003 drawing: pad size, tabs, odd-row face, board thickness |
| v0.3 stick design | 🧊 | archived at `f83c855`; superseded by v0.4 |
| v0.3 CM5 position | ✅ | matches Raspberry Pi's CM5 3D model (RP-007222-DD-2) |
| v0.3 fab files | ✅ | `hardware/v0.3/dongle/fab/` from `make fab` |
| v0.2 one-board dongle | 🧊 | archived at `6d5fa2a`; superseded by v0.3 |
| v0.1 main board and mic bar | 🧊 | archived at `2c0782a`; superseded by v0.2 |
| Firmware / OS image | ❌ | not started |

States: ✅ done (gated) · 🚧 in progress · ❌ not started · 🧊 frozen/won't do.

## Current week

- **Shipping:** between cycles
- **Last release:** none
- **Known red:** none.
