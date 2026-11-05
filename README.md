# Agentcast

An HDMI dongle with a far-field mic array. Plug it into any TV; people in
the room talk, a cloud agent does the work, and the TV shows the results.
The product spec is [`docs/office-agent-dongle.md`](docs/office-agent-dongle.md).

## Hardware versions

| Version | State | Boards | Notes |
|---|---|---|---|
| [v0.4](hardware/v0.4/) | in work | the v0.3 stick with a male HDMI Type-A plug on its end: plugs straight into the TV | Gates GREEN. Plug footprint awaits the plug's drawing (4 numbers). Not yet ordered. |
| [v0.3](hardware/v0.3/) | archived | one board, 67 x 46 mm stick: CM5 carrier, HDMI-A at the end, USB-C power and USB-C external mic on the sides, on-board mic, hardware mute | Gates GREEN. CM5 position checked against Raspberry Pi's 3D model. Fab files in `hardware/v0.3/dongle/fab/`. Not yet ordered. |
| [v0.2](hardware/v0.2/) | archived | one board, 57 x 50.4 mm: CM5 carrier, HDMI-A, USB-C power, USB-C port for an external mic, on-board mic, hardware mute | Gates GREEN. Fab files in `hardware/v0.2/dongle/fab/`. Not yet ordered. |
| [v0.1](hardware/v0.1/) | archived | main (CM5 carrier) and mic bar (4 mics) on a cable | Gates GREEN on both boards. Never ordered. |

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
