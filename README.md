# Agentcast

An HDMI dongle with a far-field mic array. Plug it into any TV; people in
the room talk, a cloud agent does the work, and the TV shows the results.
The product spec is [`docs/office-agent-dongle.md`](docs/office-agent-dongle.md).

## Hardware versions

| Version | State | Boards | Notes |
|---|---|---|---|
| [v0.1](hardware/v0.1/) | in work | main (CM5 carrier, HDMI-A, USB-C), mic bar (4 x ICS-43434, hardware mute) | Gates GREEN on both boards. Not yet ordered. |

## Tools

The boards are designed as code and checked with the
[Via EE Workcenter](https://github.com/ThyFriendlyFox/via): KiCad 10,
ngspice and FreeRouting, driven by `workcenter`. Each board folder holds a
`design.py`; the KiCad files beside it are generated from it.

```bash
make verify
```

## How work is run

[`agent-kit/ROUTING.md`](agent-kit/ROUTING.md) says which file governs
which job. Agents read [`CLAUDE.md`](CLAUDE.md) first.
