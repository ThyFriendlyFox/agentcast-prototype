# STATUS.md — where the project actually stands

The single source of truth for project state. Claims require evidence: a
passing gate, a linked run, a tag. Updated in the same commit as the
behavior change. The weekly cycle (WEEKLY.md step 5) refreshes it.

| Area | State | Evidence |
|---|---|---|
| v0.2 one-board dongle design | ✅ | `workcenter gates` GREEN: ERC 0/0, DRC 0 errors, SIM 1 deck, EXPORT 24 Gerbers |
| v0.2 fab files | ✅ | `hardware/v0.2/dongle/fab/` from `make fab` |
| v0.2 board ordered | ❌ | blocked on checking CM5 socket positions |
| v0.1 main board and mic bar | 🧊 | archived at `2c0782a`; superseded by v0.2 |
| Firmware / OS image | ❌ | not started |

States: ✅ done (gated) · 🚧 in progress · ❌ not started · 🧊 frozen/won't do.

## Current week

- **Shipping:** between cycles
- **Last release:** none
- **Known red:** none.
