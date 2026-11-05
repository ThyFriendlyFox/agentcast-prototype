#!/usr/bin/env python3
"""Write agentcast.kicad_sym: one symbol per CM5 board-to-board connector, and the ICS-43434
with a tri-state SD pin.

KiCad's libraries stop at Conn_02x40_Odd_Even and have no Compute Module 5
symbol. The pin names come from cm5_pins.csv, which was read from the CM5
datasheet (Raspberry Pi Ltd, "Raspberry Pi Compute Module 5", section 4.2,
pinout table). CM5 pin N on connector 2 (pins 101-200) is pad N-100 of the
Hirose DF40C-100DS footprint.

    python3 gen_library.py        # rewrites agentcast.kicad_sym beside it
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "(effects (font (size 1.27 1.27)))"
HIDE = "(effects (font (size 1.27 1.27)) (hide yes))"
PIN_X = 20.32  # pin root; the box edge sits one pin length (2.54) inside it
TOP = 62.23  # first row, 49 x 1.27 so every pin lands on the 1.27 mm grid


def pins() -> dict[int, str]:
    with (HERE / "cm5_pins.csv").open(encoding="utf-8") as f:
        return {int(r["pin"]): r["signal"] for r in csv.DictReader(f)}


def symbol(name: str, first: int, table: dict[int, str]) -> str:
    rows = []
    for i in range(50):
        y = round(TOP - 2.54 * i, 2)
        odd, even = first + 2 * i, first + 2 * i + 1
        for cm5_pin, x, ang in ((odd, -PIN_X, 0), (even, PIN_X, 180)):
            pad = cm5_pin - first + 1
            kind = "power_in" if table[cm5_pin] == "GND" else "passive"
            label = f"{table[cm5_pin]}_{cm5_pin}"  # KiCad turns a space into _ in open-pin net names
            rows.append(
                f'      (pin {kind} line (at {x} {y} {ang}) (length 2.54)'
                f' (name "{label}" {FONT}) (number "{pad}" {FONT}))'
            )
    body = "\n".join(rows)
    h = TOP + 2.54
    return f"""  (symbol "{name}" (pin_names (offset 0.508)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "J" (at 0 {h + 1.27} 0) {FONT})
    (property "Value" "{name}" (at 0 {-h - 1.27} 0) {FONT})
    (property "Footprint" "Connector_Hirose_DF40:Hirose_DF40C-100DS-0.4V_2x50_P0.4mm" (at 0 0 0) {HIDE})
    (property "Datasheet" "https://datasheets.raspberrypi.com/cm5/cm5-datasheet.pdf" (at 0 0 0) {HIDE})
    (property "Description" "Raspberry Pi CM5 connector, CM5 pins {first}-{first + 99}; pad = CM5 pin - {first - 1}" (at 0 0 0) {HIDE})
    (symbol "{name}_0_1"
      (rectangle (start -17.78 {h}) (end 17.78 {-h}) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "{name}_1_1"
{body}
    )
  )"""


def ics43434_tristate() -> str:
    """KiCad's ICS-43434 with SD as tri_state, as the part drives SD only in its own half of the
    WS frame (ICS-43434 datasheet, "I2S data interface"); two mics share one SD line, which the
    library's plain output type reports as a short."""
    lib = Path("/usr/share/kicad/symbols/Sensor_Audio.kicad_sym").read_text(encoding="utf-8")
    start = lib.index('(symbol "ICS-43434"')
    depth, i = 0, start
    while True:
        depth += {"(": 1, ")": -1}.get(lib[i], 0)
        i += 1
        if depth == 0:
            break
    sym = lib[start:i].replace('"ICS-43434', '"ICS-43434_TS')
    head = sym.split('(number "6"', 1)[0]
    k = head.rindex("(pin output")
    return sym[:k] + "(pin tri_state" + sym[k + len("(pin output") :]


# HDMI Type-A male plug clamped on the board edge (a "straddle" or "clamp plate" plug, e.g. XUNPU
# HDMI-003, LCSC C5723179). Contact layout from the HDMI Type-A pinout: 19 contacts in two rows,
# odd pins in one row and even pins in the other, 1.0 mm apart in a row, the rows 0.5 mm apart.
# The numbers below marked PART are the plug's own and still need its drawing: pad length, the
# clamp tabs, and which board face carries the odd row (ODD_ON_TOP).
PLUG_PITCH = 1.0  # contact pitch in one row (HDMI Type-A)
PLUG_PAD = (0.6, 2.0)  # PART: pad width along the row, length in from the edge
PLUG_EDGE_GAP = 0.3  # pads stop this far from the board edge (the board's copper-edge rule)
PLUG_TAB_X, PLUG_TAB = 6.6, (1.2, 2.4)  # PART: clamp tab centre from the plug axis, tab size
PLUG_BODY = (13.9, 11.5, 4.45)  # shell width, length beyond the edge, height (HDMI Type-A plug)
ODD_ON_TOP = True  # PART


def plug_footprint(name: str, pins: list[int], mirror: bool) -> str:
    """One face of the plug: the pads of `pins` along the edge (y = 0 is the board edge, the plug
    beyond it at +y), pin 1's end at +x. `mirror` lays the row out for a part placed on B.Cu."""
    w, l = PLUG_PAD
    y = -(PLUG_EDGE_GAP + l / 2)
    sign = -1 if mirror else 1
    pads = []
    for k in pins:
        x = sign * (4.5 - (k - 1) * 0.5)
        pads.append(f'  (pad "{k}" smd rect (at {x:.3f} {y:.3f}) (size {w} {l}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    tw, tl = PLUG_TAB
    ty = -(PLUG_EDGE_GAP + tl / 2)
    for tx in (-PLUG_TAB_X, PLUG_TAB_X):
        pads.append(f'  (pad "SH" smd rect (at {tx:.3f} {ty:.3f}) (size {tw} {tl}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    bw, bl, _ = PLUG_BODY
    cy1, cy2 = -(PLUG_EDGE_GAP + max(l, tl) + 0.25), bl + 0.25
    cx = bw / 2 + 0.25
    bom = "" if not mirror else " exclude_from_bom"
    return f"""(footprint "{name}" (version 20241229) (generator "agentcast_gen_library") (layer "F.Cu")
  (descr "HDMI Type-A male plug on the board edge, {'even' if mirror else 'odd'} contacts; pitch from the HDMI Type-A pinout, pad and tab sizes to confirm against the plug's drawing")
  (attr smd{bom})
  (property "Reference" "J" (at 0 {cy1 - 1:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "{name}" (at 0 {bl / 2:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_line (start {-bw / 2} 0) (end {bw / 2} 0) (stroke (width 0.1) (type solid)) (layer "Dwgs.User"))
  (fp_text user "PCB Edge" (at 0 0.6 0) (layer "Dwgs.User") (effects (font (size 0.5 0.5) (thickness 0.08))))
  (fp_rect (start {-bw / 2} 0) (end {bw / 2} {bl}) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))
  (fp_rect (start {-cx:.2f} {cy1:.2f}) (end {cx:.2f} {cy2:.2f}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
{chr(10).join(pads)}
)
"""


HDMI_PIN_NAMES = {
    1: "D2+", 2: "D2S", 3: "D2-", 4: "D1+", 5: "D1S", 6: "D1-", 7: "D0+", 8: "D0S", 9: "D0-",
    10: "CK+", 11: "CKS", 12: "CK-", 13: "CEC", 14: "UTILITY", 15: "SCL", 16: "SDA", 17: "GND",
    18: "+5V", 19: "HPD",
}  # fmt: skip


def plug_symbol(name: str, pins: list[int]) -> str:
    """One face of the HDMI plug as a symbol: its contacts down the left, the shell (SH) below."""
    rows = []
    for i, k in enumerate(pins):
        y = round(12.7 - 2.54 * i, 2)
        rows.append(
            f'      (pin passive line (at -10.16 {y} 0) (length 2.54)'
            f' (name "{HDMI_PIN_NAMES[k]}" {FONT}) (number "{k}" {FONT}))'
        )
    rows.append(f'      (pin passive line (at 0 -17.78 90) (length 2.54) (name "SH" {FONT}) (number "SH" {FONT}))')
    return f"""  (symbol "{name}" (pin_names (offset 0.508)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "J" (at 0 16.51 0) {FONT})
    (property "Value" "{name}" (at 0 -20.32 0) {FONT})
    (property "Footprint" "" (at 0 0 0) {HIDE})
    (property "Datasheet" "https://www.lcsc.com/product-detail/C5723179.html" (at 0 0 0) {HIDE})
    (property "Description" "HDMI Type-A male plug, one board face" (at 0 0 0) {HIDE})
    (symbol "{name}_0_1"
      (rectangle (start -7.62 15.24) (end 7.62 -15.24) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "{name}_1_1"
{chr(10).join(rows)}
    )
  )"""


def main() -> None:
    odd, even = list(range(1, 20, 2)), list(range(2, 19, 2))
    top, bottom = (odd, even) if ODD_ON_TOP else (even, odd)
    table = pins()
    text = (
        "(kicad_symbol_lib (version 20241209) (generator \"agentcast_gen_library\")\n"
        + symbol("CM5_J1", 1, table)
        + "\n"
        + symbol("CM5_J2", 101, table)
        + "\n"
        + ics43434_tristate()
        + "\n"
        + plug_symbol("HDMI_A_Plug_Top", top)
        + "\n"
        + plug_symbol("HDMI_A_Plug_Bottom", bottom)
        + "\n)\n"
    )
    (HERE / "agentcast.kicad_sym").write_text(text, encoding="utf-8")
    pretty = HERE / "agentcast.pretty"
    pretty.mkdir(exist_ok=True)
    (pretty / "HDMI_A_Plug_Edge_Top.kicad_mod").write_text(
        plug_footprint("HDMI_A_Plug_Edge_Top", top, False), encoding="utf-8"
    )
    (pretty / "HDMI_A_Plug_Edge_Bottom.kicad_mod").write_text(
        plug_footprint("HDMI_A_Plug_Edge_Bottom", bottom, True), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
