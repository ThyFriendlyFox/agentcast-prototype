# VERIFICATION.md — one command answers "is this repo healthy"

`make verify` runs, in order:

1. Lint / format check — `make lint`
2. Gates — `make gates`: `workcenter gates` (ERC, DRC, SIM, EXPORT) on every
   board of the version in work.

`make design` (regenerate and route) is not part of verify: it rewrites the
boards. Run it after a design change, then verify.

## Rules

- CI runs **the same command** as local. No CI-only logic.
- A gate that can't run in some environment **skips loudly**, never
  passes silently.
- New behavior lands with its gate in the same PR whenever feasible.
- A feature's completion promise (ROADMAP.md) should be backed by a gate
  here whenever it can be — evidence that keeps proving itself beats
  evidence produced once.
- Fixing a flaky or broken gate is always in scope, for any task.
