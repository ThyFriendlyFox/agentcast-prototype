# AGENTS.md — the binding contract

In effect whenever code in this repo is touched, by agent or human.
When this conflicts with intuition, this wins.

## Commands

```sh
make design      # regenerate and route every board from its design.py (slow; FreeRouting)
make gates       # workcenter gates on every board of the version in work: ERC, DRC, SIM, EXPORT
make lint        # byte-compile and ruff-check the design and generator scripts
make verify      # lint + gates: must pass before any push
```

Requires the EE Workcenter toolchain (KiCad 10.0, ngspice 42, FreeRouting 1.9.0, Python 3.12; `workcenter doctor`).

## Invariants — never regress these

1. Each board is generated from its `design.py` by the EE Workcenter
   (`workcenter design`). Nobody edits a generated `.kicad_*` file by hand;
   hand-routed copper lives in `build()`.
2. `workcenter gates <board>` is GREEN for every board of the version in
   work before a push. The workcenter's gates (ERC, DRC, SIM, EXPORT) bind
   this repo; this repo may add gates, never remove one.
3. Hardware lives in version folders (`hardware/v0.1/`, ...). A new feature
   is a new version folder (Via `PROCESSES.md` P22); a pushed version only
   takes fixes.
4. The CM5 pin table (`hardware/*/library/cm5_pins.csv`) is read from the
   CM5 datasheet, never typed from memory. Symbols come from it via
   `gen_library.py`.
5. The mute path stays hardware: MIC_VDD runs through the mute switch, and
   the mic, its clock buffers, the LIVE LED and the external port's power
   switch all run from MIC_VDD. No firmware or GPIO may power any of them.

## Landmine map

<!-- Places where the obvious change is the wrong change. -->

| Area | Why it bites |
|---|---|
| `hardware/*/dongle/design.py` TMDS routes | The four HDMI pairs are drawn by hand (`route_tmds`) at 0.2/0.2 mm for 100 ohm on the JLC04161H-7628 stackup. Moving J2 or J3 moves every point; re-check the skew table the function prints. |
| CM5 socket placement | From CM5 datasheet Figure 4 (approximate). Check it against Raspberry Pi's CM5 design files before ordering boards. |
| Antenna keep-out | The pours are cut under the CM5's PCB antenna. A new pour or part in that corner detunes Wi-Fi. |
| `gen_library.py` pin names | No spaces in pin names: KiCad writes a space as `_` in an open pin's net name and the DRC parity check fails. |
| Build output | `build/` is the workcenter's output (gates, renders, Gerbers). It is ignored; pictures a README shows are copied to the version's `docs/`. |

## House style

- Match the surrounding code's idiom, naming, and comment density.
- No demo scaffolding, no leftover diagnostics, no dead flags.
- Comments state constraints the code can't show — never narration.
- User-facing copy states the thing plainly; no reassurance microcopy.

## Process rules

- Branch from `main`; never commit to it directly.
- `make verify` green before every push. Flaky gate → fix or
  quarantine in the same PR; never route around it.
- After adding/removing/renaming source files, run the stack's
  regeneration step (project gen, lockfile, tidy) and commit the result.
- Commit at boundaries; message says what changed and cites evidence.
- Docs move with behavior — same commit or PR.
- Report outcomes faithfully; failing is failing, with output.
