# Architecture

Agentcast is hardware designed as code: Python design files that the Via EE
Workcenter turns into KiCad 10 projects. The repo has 3 parts.

| Part | Folder | Task |
|---|---|---|
| Library | `hardware/<version>/library/` | The CM5 pin table (from the datasheet) and the project symbols made from it. |
| Main board | `hardware/<version>/main/` | CM5 carrier: HDMI-A out, USB-C power, mic bar socket. |
| Mic bar | `hardware/<version>/micbar/` | 4 I2S mics, hardware mute, state LEDs. |

## Data flow

1. A person speaks; the mic bar's 4 mics sample on the CM5's I2S0 clock.
2. The samples travel the 10-way cable on 2 data lanes to the CM5 (GPIO20, GPIO22).
3. The CM5 streams the audio to the cloud agent over Wi-Fi.
4. The agent's results come back and the CM5 draws them on HDMI0.
5. The TV shows them; CEC wakes the TV and selects its input.

## Boundaries

| Boundary | Rule |
|---|---|
| design.py ↔ KiCad files | The KiCad files are generated. Change `design.py`, never the `.kicad_*` files. |
| main ↔ mic bar | The cable carries 3.3 V, I2S, MIC_LIVE and STATE_LED only. The pinout is in `hardware/<version>/README.md`; both ends change together. |
| CM5 GPIO ↔ mic power | No GPIO powers the mics or the LIVE LED. Only SW1 does. |
| this repo ↔ Via | Via is read-only here. Its gates bind every board. |
