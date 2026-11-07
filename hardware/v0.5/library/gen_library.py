#!/usr/bin/env python3
"""Write the Agentcast v0.5 library: agentcast.kicad_sym and agentcast.pretty/.

KiCad 10's libraries have none of these:

- ESP32-P4 (Espressif): symbol from esp32p4_pins.csv, read from the ESP32-P4 Series Datasheet v0.7,
  Table 2-1 (pin overview); QFN104 footprint from its Figure 6-1 (10 x 10 mm, 0.35 mm pitch,
  lead 0.18 x 0.4 mm, exposed pad 7.5 mm).
- LT8912B (Lontium MIPI DSI to HDMI bridge): symbol from lt8912b_pins.csv, read from the LT8912B
  datasheet R1.13, Table 6.2.1; QFN64 footprint from its Figure 9.2.1 (recommended footprint:
  0.2 x 1.3 mm pads at 0.4 mm, 9.1 mm across the pads' outer ends, exposed pad 6.2 mm).
- ICS-43434 with SD as tri-state (KiCad's has it as output; two mics on one line read as a short).
- HDMI Type-A male plug XUNPU HDMI-003 (LCSC C5723179), from its manufacturer drawing
  ("HDMI A TYPE", recommended PCB layout): even contacts 2-18 on the top face, odd contacts 1-19
  on the bottom, 0.70 mm pads at 1.00 mm pitch, 3.00 mm long from the board edge; shell tabs
  2.20 x 2.20 mm (top) and 3.05 x 2.20 mm (bottom) 13.60 mm apart; two 0.60 mm slots 0.80 mm
  deep in the board edge at the tabs; board 1.60 mm thick.

    python3 gen_library.py        # rewrites agentcast.kicad_sym and agentcast.pretty/ beside it
"""

from __future__ import annotations

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
FONT = "(effects (font (size 1.27 1.27)))"
HIDE = "(effects (font (size 1.27 1.27)) (hide yes))"


def table(name: str) -> dict[int, str]:
    with (HERE / name).open(encoding="utf-8") as f:
        return {int(r["pin"]): r["name"] for r in csv.DictReader(f)}


def box_symbol(name: str, ref: str, pins: dict[int, str], descr: str, datasheet: str) -> str:
    """A rectangle with the first half of the pins down the left, the rest down the right.

    Pins sit on the 2.54 mm grid; names carry the pin number so repeated names stay apart."""
    numbers = sorted(pins)
    half = (len(numbers) + 1) // 2
    sides = ((numbers[:half], -20.32, 0), (numbers[half:], 20.32, 180))
    top = 2.54 * ((half - 1) // 2 + 1) - 1.27 * ((half - 1) % 2) if half % 2 == 0 else 2.54 * ((half - 1) // 2)
    rows = []
    for nums, x, ang in sides:
        for i, n in enumerate(nums):
            y = round(top - 2.54 * i, 2)
            kind = "power_in" if pins[n] == "GND" else "passive"
            rows.append(
                f"      (pin {kind} line (at {x} {y} {ang}) (length 2.54)"
                f' (name "{pins[n]}" {FONT}) (number "{n}" {FONT}))'
            )
    h = top + 2.54
    bottom = top - 2.54 * (half - 1) - 2.54
    return f"""  (symbol "{name}" (pin_names (offset 0.508)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "{ref}" (at 0 {h + 1.27:.2f} 0) {FONT})
    (property "Value" "{name}" (at 0 {bottom - 1.27:.2f} 0) {FONT})
    (property "Footprint" "" (at 0 0 0) {HIDE})
    (property "Datasheet" "{datasheet}" (at 0 0 0) {HIDE})
    (property "Description" "{descr}" (at 0 0 0) {HIDE})
    (symbol "{name}_0_1"
      (rectangle (start -17.78 {h:.2f}) (end 17.78 {bottom:.2f}) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "{name}_1_1"
{chr(10).join(rows)}
    )
  )"""


def ics43434_tristate() -> str:
    """KiCad's ICS-43434 with SD as tri_state, as the part drives SD only in its own half of the
    WS frame (ICS-43434 datasheet, "I2S data interface")."""
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
            f"      (pin passive line (at -10.16 {y} 0) (length 2.54)"
            f' (name "{HDMI_PIN_NAMES[k]}" {FONT}) (number "{k}" {FONT}))'
        )
    rows.append(f'      (pin passive line (at 0 -17.78 90) (length 2.54) (name "SH" {FONT}) (number "SH" {FONT}))')
    return f"""  (symbol "{name}" (pin_names (offset 0.508)) (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "J" (at 0 16.51 0) {FONT})
    (property "Value" "{name}" (at 0 -20.32 0) {FONT})
    (property "Footprint" "" (at 0 0 0) {HIDE})
    (property "Datasheet" "https://www.lcsc.com/product-detail/C5723179.html" (at 0 0 0) {HIDE})
    (property "Description" "HDMI Type-A male plug XUNPU HDMI-003, one board face" (at 0 0 0) {HIDE})
    (symbol "{name}_0_1"
      (rectangle (start -7.62 15.24) (end 7.62 -15.24) (stroke (width 0.254) (type default)) (fill (type background)))
    )
    (symbol "{name}_1_1"
{chr(10).join(rows)}
    )
  )"""


def pad(number: str, x: float, y: float, w: float, h: float, layers: str = '"F.Cu" "F.Paste" "F.Mask"') -> str:
    return f'  (pad "{number}" smd rect (at {x:.4f} {y:.4f}) (size {w:.4f} {h:.4f}) (layers {layers}))'


def qfn(name: str, descr: str, n: int, pitch: float, pad_w: float, pad_in: float, pad_out: float,
        ep: float, body: float, paste: int) -> str:
    """A square QFN, 4 x `n` pads numbered anticlockwise from pin 1 at the top of the left side (as
    both datasheets draw them), pads from `pad_in` to `pad_out` off the centre, an exposed pad of
    side `ep` numbered 4n+1 with a `paste` x `paste` grid of paste windows."""
    c, ln = (pad_in + pad_out) / 2, pad_out - pad_in
    first = -(n - 1) / 2 * pitch
    pads = []
    for i in range(n):
        o = first + i * pitch
        pads.append(pad(str(1 + i), -c, o, ln, pad_w))  # left, down
        pads.append(pad(str(n + 1 + i), o, c, pad_w, ln))  # bottom, rightwards
        pads.append(pad(str(2 * n + 1 + i), c, -o, ln, pad_w))  # right, up
        pads.append(pad(str(3 * n + 1 + i), -o, -c, pad_w, ln))  # top, leftwards
    pads.append(pad(str(4 * n + 1), 0, 0, ep, ep, '"F.Cu" "F.Mask"'))
    cell = ep / paste
    for i in range(paste):
        for j in range(paste):
            x, y = -ep / 2 + cell * (i + 0.5), -ep / 2 + cell * (j + 0.5)
            pads.append(pad("", x, y, cell * 0.7, cell * 0.7, '"F.Paste"'))
    b, cy = body / 2, pad_out + 0.25
    return f"""(footprint "{name}" (version 20241229) (generator "agentcast_gen_library") (layer "F.Cu")
  (descr "{descr}")
  (attr smd)
  (property "Reference" "U" (at 0 {-cy - 1:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "{name}" (at 0 {cy + 1:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start {-b} {-b}) (end {b} {b}) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))
  (fp_circle (center {-b + 0.6} {-b + 0.6}) (end {-b + 0.8} {-b + 0.6}) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))
  (fp_circle (center {-cy - 0.3} {first - 0.3}) (end {-cy - 0.2} {first - 0.3}) (stroke (width 0.2) (type solid)) (fill no) (layer "F.SilkS"))
  (fp_rect (start {-cy:.2f} {-cy:.2f}) (end {cy:.2f} {cy:.2f}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
{chr(10).join(pads)}
)
"""


# XUNPU HDMI-003 recommended PCB layout (manufacturer drawing). y = 0 is the board edge, the plug
# beyond it at +y; x is seen from the top face, pin 1's end at +x.
PLUG_PAD = (0.70, 3.00)  # width, length in from the edge
PLUG_EDGE_GAP = 0.30  # the pads stop this far short of the edge: the board's copper-to-edge rule
PLUG_TAB_X = 6.80  # tab and slot centres, 13.60 mm apart
PLUG_TAB_TOP = (2.20, 2.20)  # centred on the slot
PLUG_TAB_BOTTOM = (3.05, 2.20, 1.10)  # width, height, inner edge from the slot centre
PLUG_TAB_Y = (2.10, 4.30)  # tab from / to, in from the edge
PLUG_SLOT = (0.60, 0.80)  # width, depth (cut in the board edge; see design.py)
PLUG_BODY = (13.90, 11.30, 4.45)  # shell width, length beyond the edge, height
PLUG_SHELL_BELOW = 1.30  # the shell's underside sits this far below the board's underside


def plug_footprint(name: str, bottom: bool) -> str:
    """One face of the plug: the top face carries pins 2-18, the bottom face pins 1-19. The bottom
    footprint is drawn as seen from the top and mirrored in x, as the part is placed on B.Cu."""
    w, ln = PLUG_PAD
    pins = range(1, 20, 2) if bottom else range(2, 19, 2)
    s = -1 if bottom else 1
    y = -(PLUG_EDGE_GAP + (ln - PLUG_EDGE_GAP) / 2)
    # Drawing, top view, plug pointing away from the board: pin 2 at the left. Here the plug points
    # to +y (down the page), so pin 1's end is at +x.
    pads = [pad(str(k), s * (4.5 - (k - 1) * 0.5), y, w, ln - PLUG_EDGE_GAP) for k in pins]
    ty = -(PLUG_TAB_Y[0] + PLUG_TAB_Y[1]) / 2
    th = PLUG_TAB_Y[1] - PLUG_TAB_Y[0]
    for side in (-1, 1):
        if bottom:
            tw, _, inner = PLUG_TAB_BOTTOM
            cx = side * (PLUG_TAB_X - inner + tw / 2)
        else:
            tw, cx = PLUG_TAB_TOP[0], side * PLUG_TAB_X
        pads.append(pad("SH", s * cx, ty, tw, th))
    bw, bl, _ = PLUG_BODY
    cy1 = -(PLUG_TAB_Y[1] + 0.25)
    cx = PLUG_TAB_X + 2.0
    bom = " exclude_from_bom" if bottom else ""
    edge = [
        f'  (fp_line (start {-bw / 2} 0) (end {bw / 2} 0) (stroke (width 0.1) (type solid)) (layer "Dwgs.User"))',
        '  (fp_text user "PCB Edge" (at 0 0.6 0) (layer "Dwgs.User") (effects (font (size 0.5 0.5) (thickness 0.08))))',
    ]
    return f"""(footprint "{name}" (version 20241229) (generator "agentcast_gen_library") (layer "F.Cu")
  (descr "XUNPU HDMI-003 HDMI Type-A male plug on the board edge, {'bottom face, pins 1-19' if bottom else 'top face, pins 2-18'}; manufacturer drawing, recommended PCB layout")
  (attr smd{bom})
  (property "Reference" "J" (at 0 {cy1 - 1:.2f} 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "{name}" (at 0 {bl / 2:.2f} 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
{chr(10).join(edge)}
  (fp_rect (start {-bw / 2} 0) (end {bw / 2} {bl}) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))
  (fp_rect (start {-cx:.2f} {cy1:.2f}) (end {cx:.2f} {bl + 0.25:.2f}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
{chr(10).join(pads)}
)
"""


def main() -> None:
    p4, lt = table("esp32p4_pins.csv"), table("lt8912b_pins.csv")
    symbols = [
        box_symbol("ESP32-P4", "U", p4, "ESP32-P4NRW32 (QFN104, 32 MB PSRAM in package); pin 105 is the exposed pad",
                   "https://documentation.espressif.com/esp32-p4_datasheet_en.pdf"),
        box_symbol("LT8912B", "U", lt, "Lontium LT8912B MIPI DSI to HDMI bridge (QFN64); pin 65 is the exposed pad",
                   "https://www.lontiumsemi.com"),
        ics43434_tristate(),
        plug_symbol("HDMI_A_Plug_Top", list(range(2, 19, 2))),
        plug_symbol("HDMI_A_Plug_Bottom", list(range(1, 20, 2))),
    ]
    text = '(kicad_symbol_lib (version 20241209) (generator "agentcast_gen_library")\n'
    text += "\n".join(symbols) + "\n)\n"
    (HERE / "agentcast.kicad_sym").write_text(text, encoding="utf-8")
    pretty = HERE / "agentcast.pretty"
    pretty.mkdir(exist_ok=True)
    footprints = {
        # ESP32-P4: lead 4.6-5.0 mm off centre; pad 4.6-5.2 mm (toe +0.2), 0.19 mm wide (0.16 gap).
        "QFN-104-1EP_10x10mm_P0.35mm_EP7.5x7.5mm": qfn(
            "QFN-104-1EP_10x10mm_P0.35mm_EP7.5x7.5mm",
            "ESP32-P4 QFN104, ESP32-P4 Series Datasheet v0.7 Figure 6-1", 26, 0.35, 0.19, 4.6, 5.2, 7.5, 10.0, 3),
        # LT8912B: Figure 9.2.1, pads 3.25-4.55 mm off centre (6.5 / 9.1 mm across), 0.2 mm wide.
        "QFN-64-1EP_7.5x7.5mm_P0.4mm_EP6.2x6.2mm": qfn(
            "QFN-64-1EP_7.5x7.5mm_P0.4mm_EP6.2x6.2mm",
            "LT8912B QFN64, LT8912B datasheet R1.13 Figure 9.2.1", 16, 0.4, 0.2, 3.25, 4.55, 6.2, 7.5, 3),
        "HDMI_A_Plug_XUNPU_HDMI-003_Top": plug_footprint("HDMI_A_Plug_XUNPU_HDMI-003_Top", False),
        "HDMI_A_Plug_XUNPU_HDMI-003_Bottom": plug_footprint("HDMI_A_Plug_XUNPU_HDMI-003_Bottom", True),
    }
    for old in pretty.glob("*.kicad_mod"):
        if old.stem not in footprints:
            old.unlink()
    for name, body in footprints.items():
        (pretty / f"{name}.kicad_mod").write_text(body, encoding="utf-8")


if __name__ == "__main__":
    main()
