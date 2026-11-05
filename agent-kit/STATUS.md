# STATUS.md — where the project actually stands

The single source of truth for project state. Claims require evidence: a
passing gate, a linked run, a tag. Updated in the same commit as the
behavior change. The weekly cycle (WEEKLY.md step 5) refreshes it.

| Area | State | Evidence |
|---|---|---|
| v0.3 stick design | ✅ | `workcenter gates` GREEN: ERC 0/0, DRC 0 errors, SIM 1 deck, EXPORT 24 Gerbers; `render --strict` passes |
| v0.3 CM5 position | ✅ | matches Raspberry Pi's CM5 3D model (RP-007222-DD-2) |
| v0.3 fab files | ✅ | `hardware/v0.3/dongle/fab/` from `make fab` |
| v0.3 board ordered | ❌ | HDMI plug question open (receptacle plus adapter in v0.3) |
| v0.2 one-board dongle | 🧊 | archived at `6d5fa2a`; superseded by v0.3 |
| v0.1 main board and mic bar | 🧊 | archived at `2c0782a`; superseded by v0.2 |
| Firmware / OS image | ❌ | not started |

States: ✅ done (gated) · 🚧 in progress · ❌ not started · 🧊 frozen/won't do.

## Current week

- **Shipping:** between cycles
- **Last release:** none
- **Known red:** none.
