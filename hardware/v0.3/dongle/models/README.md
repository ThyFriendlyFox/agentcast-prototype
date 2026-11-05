# 3D bodies

Every part on the board has a 3D body; `workcenter render --strict` checks it.
The library has bodies for all but the CM5 sockets.

| File | What | Source |
|---|---|---|
| `df40c_100ds.wrl` | Hirose DF40C-100DS socket, a box (KiCad 10 ships no body for it) | Via `tools/wrlgen.py`, command below |
| `cm5.step` | Raspberry Pi CM5, for assembly pictures only. Not in git. | `make cm5-model` (Raspberry Pi document RP-007222-DD-2) |

```bash
python3 tools/wrlgen.py leadless models/df40c_100ds.wrl --body 22.4 3.6 1.0 --pins 50 0 --pitch 0.4 --terminal 0.4 0.2
```
