# Agentcast

Hardware for the Agentcast dongle (`docs/office-agent-dongle.md`).

- The version in work is `hardware/v0.1/`.
- Boards are made with the Via EE Workcenter. When Via is attached, run its
  `attached-repos` skill first: this repository is the project and the only
  write target; Via is read-only. Via's gates (ERC, DRC, SIM, EXPORT) and its
  `PROCESSES.md` bind every board here.
- `agent-kit/ROUTING.md` decides which file governs a situation;
  `agent-kit/AGENTS.md` is binding whenever code here is touched.
- `make verify` is GREEN before every push.
