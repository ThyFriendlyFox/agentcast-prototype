# Architecture

Agentcast is hardware designed as code: Python design files that the Via EE
Workcenter turns into KiCad 10 projects. The repo has 3 parts.

| Part | Folder | Task |
|---|---|---|
| Library | `hardware/<version>/library/` | The CM5 pin table (from the datasheet) and the project symbols made from it. |
| Dongle | `hardware/<version>/dongle/` | The one board from v0.2: CM5 carrier, HDMI-A, USB-C power, USB-C external mic port, on-board mic, hardware mute. |

## Data flow

1. A person speaks; the on-board mic samples on the CM5's I2S0 clock, or a USB mic on J6 records.
2. The samples reach the CM5 on I2S0_SDI[0] (GPIO20) or USB.
3. The CM5 streams the audio to the cloud agent over Wi-Fi.
4. The agent's results come back and the CM5 draws them on HDMI0.
5. The TV shows them; CEC wakes the TV and selects its input.

## Boundaries

| Boundary | Rule |
|---|---|
| design.py ↔ KiCad files | The KiCad files are generated. Change `design.py`, never the `.kicad_*` files. |
| CM5 GPIO ↔ mic power | No GPIO powers a mic, the external port or the LIVE LED. Only the mute switch does. |
| this repo ↔ Via | Via is read-only here. Its gates bind every board. |
