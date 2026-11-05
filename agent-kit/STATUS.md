# STATUS.md — where the project actually stands

The single source of truth for project state. Claims require evidence: a
passing gate, a linked run, a tag. Updated in the same commit as the
behavior change. The weekly cycle (WEEKLY.md step 5) refreshes it.

| Area | State | Evidence |
|---|---|---|
| v0.1 main board design | ✅ | `workcenter gates` GREEN: ERC 0/0, DRC 0 errors, EXPORT 24 Gerbers |
| v0.1 mic bar design | ✅ | `workcenter gates` GREEN: ERC 0/0, DRC 0 errors, SIM 1 deck |
| v0.1 boards ordered | ❌ | blocked on checking CM5 socket positions |
| Firmware / OS image | ❌ | not started |

States: ✅ done (gated) · 🚧 in progress · ❌ not started · 🧊 frozen/won't do.

## Current week

- **Shipping:** between cycles
- **Last release:** none
- **Known red:** none. Main board SIM gate skips (no deck); roadmap item 2.
