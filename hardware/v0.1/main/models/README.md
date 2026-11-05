# 3D bodies

KiCad 10's 3D library has no body for these footprints. Box approximations,
made with Via's `tools/wrlgen.py`:

```bash
python3 tools/wrlgen.py leadless models/df40c_100ds.wrl --body 22.4 3.6 1.0 --pins 50 0 --pitch 0.4 --terminal 0.4 0.2
```

```bash
python3 tools/wrlgen.py leadless models/usb_c_hro_31m12.wrl --body 8.94 7.35 3.16 --pins 0 0
```
