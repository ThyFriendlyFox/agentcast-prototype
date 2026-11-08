# 3D bodies

Every part on the board has a 3D body; `workcenter render --strict` checks it.

| File | What | Source |
|---|---|---|
| `hdmi_a_plug.wrl` | XUNPU HDMI-003 shell, a box 13.9 x 11.3 x 4.45 mm (drawing's outline) | Via `tools/wrlgen.py`, command below |
| `esp32_c6_mini_1.wrl` | ESP32-C6-MINI-1, a box 13.3 x 16.7 x 2.4 mm (the footprint's fab outline, the datasheet's height); KiCad's own body is not installed in the workcenter | Via `tools/wrlgen.py`, command below |

```bash
python3 tools/wrlgen.py leadless models/hdmi_a_plug.wrl --body 13.9 11.3 4.45 --pins 0 0
python3 tools/wrlgen.py leadless models/esp32_c6_mini_1.wrl --body 13.3 16.7 2.4 --pins 0 0
```
