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


def main() -> None:
    table = pins()
    text = (
        "(kicad_symbol_lib (version 20241209) (generator \"agentcast_gen_library\")\n"
        + symbol("CM5_J1", 1, table)
        + "\n"
        + symbol("CM5_J2", 101, table)
        + "\n"
        + ics43434_tristate()
        + "\n)\n"
    )
    (HERE / "agentcast.kicad_sym").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
