# 3D bodies

Every part on the board has a 3D body; `workcenter render --strict` checks it.

| File | What | Source |
|---|---|---|
| `hdmi_a_plug.wrl` | XUNPU HDMI-003 shell, a box 13.9 x 11.3 x 4.45 mm (drawing's outline) | Via `tools/wrlgen.py`, command below |

```bash
python3 tools/wrlgen.py leadless models/hdmi_a_plug.wrl --body 13.9 11.3 4.45 --pins 0 0
```
