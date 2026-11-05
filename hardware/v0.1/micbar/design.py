"""Agentcast dongle v0.1, mic bar: four I2S MEMS microphones on a bar that sits on the TV.

The bar joins the main board by a 10-way JST SH cable (same pinout on both ends). The CM5's I2S0
is the clock master: one BCLK and one WS for all four mics, so every channel shares one clock.
Two data lanes carry two mics each (ICS-43434 L/R select).

    workcenter design design.py --route     # from this folder

Board: 140 x 14 mm, 2 layers. The bar stands on its long edge facing the room: the parts sit on
F.Cu (the back), the mics' bottom ports open through the board to B.Cu (the front), and the three
LEDs sit on B.Cu so the room sees them. The mute slide switch sticks out of the top edge.

Mute (spec "Consent, privacy and trust"): SW1 switches the mics' supply. In "live" it feeds
MIC_VDD; in "mute" it feeds the red LED and MIC_VDD has no source. The green LIVE LED runs from
MIC_VDD itself, so it is lit exactly when the mics have power; no software can change that. The
clock buffers U1 and U2 run from MIC_VDD too: with the mics off, the CM5's clocks stop at the
buffers' inputs (74LVC Ioff) and cannot feed the mics through their input clamp diodes.

Area rules (P3 step 4): no keep-out. Each mic's sound hole is a non-plated hole in its footprint;
the pours keep the edge clearance from it.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import kicadgen

BX, BY = 100.0, 100.0
W, H = 140.0, 14.0
MIC_X = [BX + 10.0, BX + 50.0, BX + 90.0, BX + 130.0]  # 40 mm pitch, 120 mm aperture
MIC_Y = BY + 7.0

# Schematic layout (P24): ref -> (x, y, angle), 2.54 mm steps, A3 sheet.
SCHEMATIC = {
    "J1": (38.1, 101.6, 0),
    "C1": (68.58, 50.8, 0),
    "SW1": (93.98, 50.8, 0),
    "R4": (129.54, 63.5, 0),
    "D2": (129.54, 78.74, 270),
    "C2": (147.32, 50.8, 0),
    "R1": (167.64, 63.5, 0),
    "D1": (167.64, 78.74, 270),
    "R5": (185.42, 63.5, 0),
    "U1": (101.6, 116.84, 0),
    "C3": (91.44, 134.62, 0),
    "U2": (101.6, 160.02, 0),
    "C4": (91.44, 177.8, 0),
    "R2": (127.0, 116.84, 90),
    "R3": (127.0, 160.02, 90),
    "MK1": (198.12, 106.68, 0),
    "C5": (220.98, 96.52, 0),
    "MK2": (198.12, 139.7, 0),
    "C6": (220.98, 129.54, 0),
    "MK3": (198.12, 172.72, 0),
    "C7": (220.98, 162.56, 0),
    "MK4": (198.12, 205.74, 0),
    "C8": (220.98, 195.58, 0),
    "R6": (63.5, 175.26, 0),
    "D3": (63.5, 190.5, 270),
}


def build() -> kicadgen.Design:
    d = kicadgen.Design(name="agentcast_micbar", namespace=uuid.UUID("2c9d41e0-6a77-4f5b-8f0e-3b5a1d7c9e21"))
    d.sheet = "A3"
    d.symbol_dirs = {"Agentcast": Path(__file__).resolve().parent.parent / "library" / "agentcast.kicad_sym"}
    d.sch_wires = True
    d.outline = (BX, BY, BX + W, BY + H)
    d.corner_radius = 2.0
    d.track_width = 0.2
    d.clearance = 0.15
    d.edge_clearance = 0.3
    d.via_size = 0.6
    d.via_drill = 0.3
    d.power_nets = {"GND": "GND", "+3V3": "+3V3", "MIC_VDD": "VDD"}
    d.flagged_nets = ["GND", "+3V3", "MIC_VDD"]
    d.check_pulls = True
    d.defined_nets = {
        "BCLK_IN": "driven by the CM5's I2S0_SCLK through R1 on the main board; U1 has Ioff",
        "WS_IN": "driven by the CM5's I2S0_WS through R2 on the main board; U2 has Ioff",
        "MIC_SD0": "100k pull-down R3 on the main board",
        "MIC_SD1": "100k pull-down R4 on the main board",
        "MIC_BCLK": "driven by U1's output through the 33 ohm series resistor R2",
        "MIC_WS": "driven by U2's output through the 33 ohm series resistor R3",
        "MUTED": "held low through R4 and D2 to GND while SW1 is in LIVE",
    }
    d.sch_label_nets = ("MIC_BCLK", "MIC_WS", "MIC_SD0", "MIC_SD1", "BCLK_IN", "WS_IN", "MIC_LIVE", "STATE_LED")

    d.add(
        "J1",
        "Connector_Generic_MountingPin:Conn_01x10_MountingPin",
        "SM10B-SRSS-TB",
        "Connector_JST:JST_SH_SM10B-SRSS-TB_1x10-1MP_P1.00mm_Horizontal",
        sch_at=(0, 0),
        pcb_at=(BX + 70.0, BY + 10.5),
        nets={
            "1": "+3V3", "2": "GND", "3": "BCLK_IN", "4": "GND", "5": "WS_IN",
            "6": "MIC_SD0", "7": "MIC_SD1", "8": "MIC_LIVE", "9": "STATE_LED", "10": "GND", "MP": "GND",
        },
    )
    d.add("C1", "Device:C_Small", "1u", "Capacitor_SMD:C_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 61.5, BY + 11.5), pcb_rot=90, nets={"1": "+3V3", "2": "GND"})  # fmt: skip
    d.add("SW1", "Switch:SW_SPDT", "PCM12SMTR", "Button_Switch_SMD:SW_SPDT_PCM12",
          sch_at=(0, 0), pcb_at=(BX + 70.0, BY + 2.6), pcb_rot=180,
          nets={"2": "+3V3", "1": "MIC_VDD", "3": "MUTED"})  # fmt: skip
    d.add("C2", "Device:C_Small", "10u", "Capacitor_SMD:C_0603_1608Metric",
          sch_at=(0, 0), pcb_at=(BX + 76.5, BY + 2.5), pcb_rot=90, nets={"1": "MIC_VDD", "2": "GND"})  # fmt: skip

    # LEDs on the front face (B.Cu): MUTED red, LIVE green (from MIC_VDD), STATE amber (CM5 GPIO6).
    d.add("R4", "Device:R_Small", "1k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 62.0, BY + 7.0), pcb_rot=90, nets={"1": "MUTED", "2": "LED_MUTED_A"})  # fmt: skip
    d.add("D2", "Device:LED", "red MUTED", "LED_SMD:LED_0603_1608Metric",
          sch_at=(0, 0), pcb_at=(BX + 64.0, BY + 4.0), pcb_layer="B.Cu", pcb_rot=90,
          nets={"2": "LED_MUTED_A", "1": "GND"})  # fmt: skip
    d.add("R1", "Device:R_Small", "1k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 78.0, BY + 7.0), pcb_rot=90, nets={"1": "MIC_VDD", "2": "LED_LIVE_A"})  # fmt: skip
    d.add("D1", "Device:LED", "green LIVE", "LED_SMD:LED_0603_1608Metric",
          sch_at=(0, 0), pcb_at=(BX + 76.0, BY + 4.0), pcb_layer="B.Cu", pcb_rot=90,
          nets={"2": "LED_LIVE_A", "1": "GND"})  # fmt: skip
    # MIC_LIVE tells the CM5 the mics have power: 10k from MIC_VDD into its 100k pull-down.
    d.add("R5", "Device:R_Small", "10k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 80.0, BY + 7.0), pcb_rot=90, nets={"1": "MIC_VDD", "2": "MIC_LIVE"})  # fmt: skip
    d.add("R6", "Device:R_Small", "330", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 67.5, BY + 6.2), pcb_rot=90, nets={"1": "STATE_LED", "2": "LED_STATE_A"})  # fmt: skip
    d.add("D3", "Device:LED", "amber STATE", "LED_SMD:LED_0603_1608Metric",
          sch_at=(0, 0), pcb_at=(BX + 70.0, BY + 5.0), pcb_layer="B.Cu", pcb_rot=90,
          nets={"2": "LED_STATE_A", "1": "GND"})  # fmt: skip

    # Clock buffers, powered from MIC_VDD (see the module docstring).
    d.add("U1", "74xGxx:74LVC1G34", "74LVC1G34", "Package_TO_SOT_SMD:SOT-353_SC-70-5",
          sch_at=(0, 0), pcb_at=(BX + 58.0, BY + 9.0), nets={"2": "BCLK_IN", "4": "BCLK_B", "3": "GND", "5": "MIC_VDD"})  # fmt: skip
    d.add("C3", "Device:C_Small", "100n", "Capacitor_SMD:C_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 58.0, BY + 11.5), nets={"1": "MIC_VDD", "2": "GND"})  # fmt: skip
    d.add("U2", "74xGxx:74LVC1G34", "74LVC1G34", "Package_TO_SOT_SMD:SOT-353_SC-70-5",
          sch_at=(0, 0), pcb_at=(BX + 82.0, BY + 9.0), nets={"2": "WS_IN", "4": "WS_B", "3": "GND", "5": "MIC_VDD"})  # fmt: skip
    d.add("C4", "Device:C_Small", "100n", "Capacitor_SMD:C_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 82.0, BY + 11.5), nets={"1": "MIC_VDD", "2": "GND"})  # fmt: skip
    # 33 ohm series resistors at the buffer outputs damp the 120 mm clock lines.
    d.add("R2", "Device:R_Small", "33", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 55.0, BY + 9.0), nets={"1": "BCLK_B", "2": "MIC_BCLK"})  # fmt: skip
    d.add("R3", "Device:R_Small", "33", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 85.0, BY + 9.0), nets={"1": "WS_B", "2": "MIC_WS"})  # fmt: skip

    # Mics: MK1/MK2 share SD0 (left/right), MK3/MK4 share SD1.
    lanes = [("MIC_SD0", "GND"), ("MIC_SD0", "MIC_VDD"), ("MIC_SD1", "GND"), ("MIC_SD1", "MIC_VDD")]
    for i, (x, (sd, lr)) in enumerate(zip(MIC_X, lanes, strict=True), start=1):
        d.add(f"MK{i}", "Agentcast:ICS-43434_TS", "ICS-43434", "Sensor_Audio:InvenSense_ICS-43434-6_3.5x2.65mm",
              sch_at=(0, 0), pcb_at=(x, MIC_Y),
              nets={"1": "MIC_WS", "2": lr, "3": "GND", "4": "MIC_BCLK", "5": "MIC_VDD", "6": sd})  # fmt: skip
        d.add(f"C{4 + i}", "Device:C_Small", "100n", "Capacitor_SMD:C_0402_1005Metric",
              sch_at=(0, 0), pcb_at=(x + 3.0, MIC_Y - 1.5), pcb_rot=90, nets={"1": "MIC_VDD", "2": "GND"})  # fmt: skip

    for part in d.parts:
        if part.ref[0] in "RCD" or part.ref == "SW1":
            part.hide_ref = True
    for ref, (x, y, rot) in SCHEMATIC.items():
        part = next(p for p in d.parts if p.ref == ref)
        part.sch_at = (x, y)
        part.sch_rot = rot

    d.zone("GND", layers=("F.Cu", "B.Cu"), connect="solid")
    d.stitch_pads("GND")
    d.text("AGENTCAST MIC v0.1", BX + 30.0, BY + 11.5, "F.SilkS", 1.0, 0.15)
    for i, x in enumerate(MIC_X, start=1):
        d.text(f"M{i}", x, BY + 2.0, "B.SilkS", 1.0, 0.15)
    return d
