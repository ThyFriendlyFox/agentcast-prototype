"""Agentcast dongle v0.1, main board: a Raspberry Pi CM5 carrier with one HDMI output.

The CM5 does the work (HDMI 2.0, Wi-Fi, CEC, I2S); this board gives it power from USB-C,
an HDMI-A receptacle, a boot button, two LEDs, and a 10-pin cable to the mic bar.

    workcenter design design.py --route     # from this folder

Board: 66 x 52.2 mm, 4 layers (F.Cu signal, In1.Cu GND plane, In2.Cu +5V pour, B.Cu signal).
The CM5 (55 x 40 mm) sits on two Hirose DF40C-100DS sockets with its antenna edge on the board's
left edge. Positions of the sockets and holes come from CM5 datasheet Figure 4 (section 4.1.1).

Area rules (P3 step 4):
- "antenna": x 100..109, y 105..126 on every layer. No track, no via; the pours are cut round it
  so no copper sits under the CM5's PCB antenna (CM5 datasheet section 2.2: keep the antenna away
  from ground planes). Nothing is placed there.
- No other keep-out. Parts stay outside the CM5 outline (x 100..155, y 100..140) except the two
  sockets and the four holes: the 1.5 mm stacking height leaves no room under the module.
"""

from __future__ import annotations

import csv
import itertools
import math
import uuid
from pathlib import Path

import kicadgen

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / "library"

BX, BY = 100.0, 100.0  # board origin, top-left
W, H = 66.0, 52.2

# CM5 placement (datasheet Figure 4): connectors centred 25.0 mm from the antenna edge, 3.0 mm
# in from the long edges; M2.5 holes 3.5 mm in from each edge.
J1_AT = (BX + 25.0, BY + 3.0)
J2_AT = (BX + 25.0, BY + 37.0)
HOLES = [(BX + 3.5, BY + 3.5), (BX + 51.5, BY + 3.5), (BX + 3.5, BY + 36.5), (BX + 51.5, BY + 36.5)]

# HDMI receptacle, opening down; its "PCB Edge" mark (5.715 mm) lands on the board edge.
HDMI_AT = (BX + 17.45, BY + 46.5)
USB_AT = (BX + 48.0, BY + 48.95)
MIC_AT = (BX + 62.5, BY + 20.0)

ANTENNA = [(BX, BY + 5.0), (BX + 9.0, BY + 5.0), (BX + 9.0, BY + 26.0), (BX, BY + 26.0)]

# TMDS pairs: 100 ohm differential on F.Cu over the In1.Cu plane. JLC04161H-7628 stackup,
# prepreg 0.2104 mm, er 4.4: w 0.2 / s 0.2 gives 104 ohm (Hammerstad-Jensen, README).
PAIR_W, PAIR_S = 0.2, 0.2


def cm5_pins() -> dict[int, str]:
    with (LIB / "cm5_pins.csv").open(encoding="utf-8") as f:
        return {int(r["pin"]): r["signal"] for r in csv.DictReader(f)}


# CM5 pin -> net for every pin this board uses (pin plan in README). GND pins are added from the
# table. Every other pin is left open, as the datasheet allows (section 4.2).
CM5_NETS = {
    21: "LED_nACT",
    26: "MIC_WS",  # GPIO19, I2S0_WS (a2)
    27: "MIC_SD0",  # GPIO20, I2S0_SDI[0] (a2)
    30: "STATE_LED",  # GPIO6, output
    34: "MIC_LIVE",  # GPIO5, input
    46: "MIC_SD1",  # GPIO22, I2S0_SDI[1] (a2)
    49: "MIC_BCLK",  # GPIO18, I2S0_SCLK (a2)
    77: "+5V",
    79: "+5V",
    81: "+5V",
    83: "+5V",
    85: "+5V",
    87: "+5V",
    78: "+3V3",  # GPIO_VREF to CM5_3.3V: 3.3 V GPIO (pin 78 must not float)
    84: "+3V3",
    86: "+3V3",
    93: "nRPIBOOT",
    94: "CC1",
    96: "CC2",
    103: "USB_DN",
    105: "USB_DP",
    151: "HDMI_CEC",
    153: "HDMI_HPD",
    170: "HDMI_D2_P",
    172: "HDMI_D2_N",
    176: "HDMI_D1_P",
    178: "HDMI_D1_N",
    182: "HDMI_D0_P",
    184: "HDMI_D0_N",
    188: "HDMI_CK_P",
    190: "HDMI_CK_N",
    199: "HDMI_SDA",
    200: "HDMI_SCL",
}

# Schematic layout (P24): ref -> (x, y, angle), 2.54 mm steps on an A2 sheet.
SCHEMATIC = {
    "J4": (50.8, 76.2, 0),
    "U1": (50.8, 132.08, 0),
    "C1": (81.28, 60.96, 0),
    "C2": (91.44, 60.96, 0),
    "J1": (162.56, 203.2, 0),
    "J2": (279.4, 203.2, 0),
    "J3": (391.16, 116.84, 0),
    "F1": (340.36, 50.8, 90),
    "D1": (365.76, 50.8, 180),
    "C3": (391.16, 60.96, 0),
    "J5": (497.84, 205.74, 0),
    "R1": (436.88, 182.88, 90),
    "R2": (436.88, 193.04, 90),
    "C4": (459.74, 160.02, 0),
    "R3": (452.12, 238.76, 0),
    "R4": (462.28, 238.76, 0),
    "R5": (472.44, 238.76, 0),
    "SW1": (93.98, 304.8, 90),
    "D2": (93.98, 342.9, 270),
    "R6": (93.98, 365.76, 0),
    "R7": (403.86, 309.88, 0),
    "D3": (403.86, 332.74, 90),
    "H1": (520.7, 355.6, 0),
    "H2": (533.4, 355.6, 0),
    "H3": (546.1, 355.6, 0),
    "H4": (558.8, 355.6, 0),
}


def jpad(at: tuple[float, float], pad: int) -> tuple[float, float]:
    """Board position of DF40C-100DS pad `pad` for a socket placed at `at`, rotated 180 degrees.

    The library footprint has pad 1 at (-9.8, 1.54), odd pads on +y, 0.4 mm along x per pad pair.
    """
    fx = -9.8 + 0.4 * ((pad - 1) // 2)
    fy = 1.54 if pad % 2 else -1.54
    return (round(at[0] - fx, 3), round(at[1] - fy, 3))


def hpad(pin: int) -> tuple[float, float]:
    """Board position of HDMI receptacle pin `pin` (Molex 208658-1001 turned 270 degrees)."""
    fy = -4.5 + 0.5 * (pin - 1)
    return (round(HDMI_AT[0] - fy, 3), round(HDMI_AT[1] - 3.285, 3))


def notched(inset: float) -> list[tuple[float, float]]:
    """The board outline, `inset` in from the edge, with the antenna area cut out."""
    x1, y1, x2, y2 = BX + inset, BY + inset, BX + W - inset, BY + H - inset
    c = 2.0  # chamfer that keeps the polygon inside the 2.5 mm corner radius
    ax, ay1, ay2 = BX + 9.0 + inset, BY + 5.0 - inset, BY + 26.0 + inset
    return [
        (x1 + c, y1), (x2 - c, y1), (x2, y1 + c), (x2, y2 - c), (x2 - c, y2), (x1 + c, y2),
        (x1, y2 - c), (x1, ay2), (ax, ay2), (ax, ay1), (x1, ay1), (x1, y1 + c),
    ]  # fmt: skip


def seg_len(points: list[tuple[float, float]]) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(points))


def pair_path(x0: float, x1: float, y0: float, ya: float, y1: float, bump: float = 0.0) -> list:
    """A TMDS trace: down from the socket pad, a V of depth `bump` (signed, along x) to lengthen
    it, a 45 degree jog of (x1 - x0) starting at `ya`, then down to the HDMI pad."""
    pts = [(x0, y0)]
    yb = BY + 39.05  # below the socket's pads
    if bump:
        pts += [(x0, yb), (x0 + bump, yb + abs(bump)), (x0, yb + 2 * abs(bump))]
    dx = x1 - x0
    pts += [(x0, ya), (x1, ya + abs(dx)), (x1, y1)]
    out = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, out[-1]) > 1e-9:
            out.append((round(p[0], 4), round(p[1], 4)))
    return out


PAIRS = [  # name, CM5 P pin, CM5 N pin, HDMI + pin, HDMI - pin
    ("D2", 170, 172, 1, 3),
    ("D1", 176, 178, 4, 6),
    ("D0", 182, 184, 7, 9),
    ("CK", 188, 190, 10, 12),
]


def route_tmds(d: kicadgen.Design) -> list[str]:
    """Hand-route the four TMDS pairs on F.Cu; returns one report line per pair (README table)."""
    report = []
    y_jog = BY + 39.75  # after the deepest bump (0.3 mm deep, 0.6 mm long)
    for name, cp, cn, hp, hn in PAIRS:
        (xp0, y0), (xn0, _) = jpad(J2_AT, cp - 100), jpad(J2_AT, cn - 100)
        (xp1, y1), (xn1, _) = hpad(hp), hpad(hn)
        # Two traces 0.4 mm apart cannot run diagonal side by side (0.28 mm between centres). A
        # trace that moves towards its partner waits until the partner's jog is done.
        dp, dn = xp1 - xp0, xn1 - xn0  # P sits right of N
        yp = yn = y_jog
        if dp < 0 < -dn or (dp < 0 and dn < 0):
            yp = y_jog + abs(dn)  # P moves left, onto N's path: N first
        if dn > 0 < dp or (dn > 0 and dp > 0):
            yn = y_jog + abs(dp)  # N moves right, onto P's path: P first
        bp = bn = 0.0
        for _ in range(2):
            p = pair_path(xp0, xp1, y0, yp, y1, bump=bp)
            n = pair_path(xn0, xn1, y0, yn, y1, bump=bn)
            skew = seg_len(p) - seg_len(n)
            if abs(skew) <= 0.05:
                break
            # lengthen the short trace with a V away from its partner
            depth = round(abs(skew) / (2 * math.sqrt(2) - 2), 3)
            if skew > 0:
                bn = -depth
            else:
                bp = depth
        d.track(f"HDMI_{name}_P", p, "F.Cu", width=PAIR_W)
        d.track(f"HDMI_{name}_N", n, "F.Cu", width=PAIR_W)
        report.append(
            f"{name}: P {seg_len(p):.3f} mm, N {seg_len(n):.3f} mm, skew {abs(seg_len(p) - seg_len(n)):.3f} mm"
        )
    return report


def tie_fine_pitch_grounds(d: kicadgen.Design, refs: tuple[str, ...]) -> None:
    """A via and a short track for each GND pad of the fine-pitch connectors.

    At 0.4 mm and 0.5 mm pitch the face pour cannot reach a pad between other nets' pads, so a via
    beside it alone stays an island. The via goes off the pad's end, along the pad's long axis,
    first on the side away from the connector's centre line, and the track joins it to the pad."""
    r, drill = d.via_size / 2, d.via_drill
    done = {(round(s[1][0], 3), round(s[1][1], 3)) for s in d.segments if s[0] == "GND"}
    for part in d.parts:
        if part.ref not in refs:
            continue
        for pad in [b for b in d.pad_boxes() if b.ref == part.ref and b.net == "GND" and b.kind == "smd"]:
            cx, cy = round((pad.x1 + pad.x2) / 2, 3), round((pad.y1 + pad.y2) / 2, 3)
            if (cx, cy) in done:
                continue  # already joined (the TMDS-side twins)
            out = 1 if cy > part.pcb_at[1] or part.ref == "J3" else -1  # J3: towards the board edge
            tall = (pad.y2 - pad.y1) > (pad.x2 - pad.x1)
            if not tall:
                continue
            boxes = d.pad_boxes()
            for side in (out, -out):
                end = pad.y2 if side > 0 else pad.y1
                vy = round(end + side * (0.12 + r), 3)
                if d._via_fits(cx, vy, r, drill, "GND", boxes):
                    d.track("GND", [(cx, cy), (cx, vy)], "F.Cu", width=0.2)
                    d.via("GND", cx, vy)
                    break


def build() -> kicadgen.Design:
    d = kicadgen.Design(name="agentcast_main", namespace=uuid.UUID("5b0f8a52-7d3e-4c1a-9e61-0a1c2e3d4f50"))
    d.copper_layers = 4
    d.plane_layers = ("In1.Cu",)
    d.sheet = "A2"
    d.sch_wires = True
    d.outline = (BX, BY, BX + W, BY + H)
    d.corner_radius = 2.5
    d.symbol_dirs = {"Agentcast": LIB / "agentcast.kicad_sym"}
    d.track_width = 0.15
    d.clearance = 0.15
    d.edge_clearance = 0.3
    d.via_size = 0.45
    d.via_drill = 0.25
    # JLCPCB 4-layer limits (README fab notes): 0.09 mm trace and gap, 0.15 mm hole, 0.25 mm via.
    d.rules = {"min_through_hole_diameter": 0.25, "min_via_diameter": 0.45}
    d.net_classes = {
        "HDMI": {
            "width": PAIR_W,
            "clearance": 0.15,
            "via": 0.45,
            "via_drill": 0.25,
            "nets": [f"HDMI_{p}_{s}" for p, *_ in PAIRS for s in "PN"],
        },
        "Power": {"width": 0.2, "clearance": 0.15, "via": 0.45, "via_drill": 0.25, "nets": ["GND", "+5V"]},
    }
    d.power_nets = {"GND": "GND", "+5V": "+5V", "+3V3": "+3V3", "+5VP": "+5VP"}
    d.flagged_nets = ["GND", "+5V", "+3V3", "+5VP"]
    d.check_pulls = True
    d.defined_nets = {
        "nRPIBOOT": "CM5 pin 93: internal 10k pull-up to CM5_3.3V (CM5 datasheet section 4.2)",
        "HDMI_SDA": "CM5 pin 199: internal 1.8k pull-up (CM5 datasheet section 4.2)",
        "HDMI_SCL": "CM5 pin 200: internal 1.8k pull-up (CM5 datasheet section 4.2)",
    }
    # Labels for the nets that cross the sheet between the two CM5 sockets and the connectors.
    d.sch_label_nets = (
        "CC1", "CC2", "USB_DP", "USB_DN", "nRPIBOOT", "LED_nACT",
        "MIC_BCLK", "MIC_WS", "MIC_SD0", "MIC_SD1", "MIC_LIVE", "STATE_LED",
        "HDMI_CEC", "HDMI_HPD", "HDMI_SDA", "HDMI_SCL",
        *[f"HDMI_{p}_{s}" for p, *_ in PAIRS for s in "PN"],
    )  # fmt: skip

    table = cm5_pins()
    sockets = (("J1", "CM5_J1", 1, J1_AT), ("J2", "CM5_J2", 101, J2_AT))
    for ref, sym, first, at in sockets:
        nets = {}
        for pin in range(first, first + 100):
            net = "GND" if table[pin] == "GND" else CM5_NETS.get(pin)
            if net:
                nets[str(pin - first + 1)] = net
        d.add(
            ref,
            f"Agentcast:{sym}",
            "DF40C-100DS-0.4V",
            "Connector_Hirose_DF40:Hirose_DF40C-100DS-0.4V_2x50_P0.4mm",
            sch_at=(0, 0),
            pcb_at=at,
            pcb_rot=180,
            nets=nets,
            descr=f"CM5 socket, CM5 pins {first}-{first + 99}",
        )

    d.add(
        "J3",
        "Connector:HDMI_A",
        "HDMI-A 208658-1001",
        "Connector_Video:HDMI_A_Molex_208658-1001_Horizontal",
        sch_at=(0, 0),
        pcb_at=HDMI_AT,
        pcb_rot=270,
        nets={
            "1": "HDMI_D2_P", "3": "HDMI_D2_N", "4": "HDMI_D1_P", "6": "HDMI_D1_N",
            "7": "HDMI_D0_P", "9": "HDMI_D0_N", "10": "HDMI_CK_P", "12": "HDMI_CK_N",
            "2": "GND", "5": "GND", "8": "GND", "11": "GND", "17": "GND", "SH": "GND",
            "13": "HDMI_CEC", "15": "HDMI_SCL", "16": "HDMI_SDA", "18": "+5VP", "19": "HDMI_HPD",
        },
    )
    # HDMI +5V (pin 18): a source supplies at least 55 mA (HDMI 1.4 section 4.2.7). The Schottky
    # stops a sink that drives its own 5 V from back-feeding the board; the PTC limits a short.
    d.add("F1", "Device:Polyfuse_Small", "0.1A hold", "Fuse:Fuse_0805_2012Metric",
          sch_at=(0, 0), pcb_at=(BX + 3.0, BY + 44.5), pcb_rot=90, nets={"1": "+5V", "2": "HDMI_5V_F"})  # fmt: skip
    d.add("D1", "Device:D_Schottky", "BAT54WS", "Diode_SMD:D_SOD-323",
          sch_at=(0, 0), pcb_at=(BX + 6.0, BY + 44.5), pcb_rot=90, nets={"2": "HDMI_5V_F", "1": "+5VP"})  # fmt: skip
    d.add("C3", "Device:C_Small", "100n", "Capacitor_SMD:C_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 6.0, BY + 48.5), pcb_rot=90, nets={"1": "+5VP", "2": "GND"})  # fmt: skip

    # USB-C: power in, and the CM5's USB 2.0 port for rpiboot flashing. CC goes to the CM5, which
    # negotiates 5 V up to 5 A itself (CM5 datasheet section 2.12.1).
    d.add(
        "J4",
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "TYPE-C-31-M-12",
        "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        sch_at=(0, 0),
        pcb_at=USB_AT,
        nets={
            "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
            "A4": "+5V", "A9": "+5V", "B4": "+5V", "B9": "+5V",
            "A5": "CC1", "B5": "CC2",
            "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
        },
    )
    d.add("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6",
          sch_at=(0, 0), pcb_at=(BX + 40.0, BY + 45.5), pcb_rot=90,
          nets={"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "+5V"})  # fmt: skip
    d.add("C1", "Device:C_Small", "22u", "Capacitor_SMD:C_0805_2012Metric",
          sch_at=(0, 0), pcb_at=(BX + 57.0, BY + 45.0), pcb_rot=90, nets={"1": "+5V", "2": "GND"})  # fmt: skip
    d.add("C2", "Device:C_Small", "22u", "Capacitor_SMD:C_0805_2012Metric",
          sch_at=(0, 0), pcb_at=(BX + 60.0, BY + 45.0), pcb_rot=90, nets={"1": "+5V", "2": "GND"})  # fmt: skip

    # Mic bar cable: JST SH 10 pins. The bar powers its mics from +3V3 through its mute switch.
    d.add(
        "J5",
        "Connector_Generic_MountingPin:Conn_01x10_MountingPin",
        "SM10B-SRSS-TB",
        "Connector_JST:JST_SH_SM10B-SRSS-TB_1x10-1MP_P1.00mm_Horizontal",
        sch_at=(0, 0),
        pcb_at=MIC_AT,
        pcb_rot=90,
        nets={
            "1": "+3V3", "2": "GND", "3": "MIC_BCLK_R", "4": "GND", "5": "MIC_WS_R",
            "6": "MIC_SD0", "7": "MIC_SD1", "8": "MIC_LIVE", "9": "STATE_LED", "10": "GND", "MP": "GND",
        },
    )
    rx = BX + 57.5
    d.add("R1", "Device:R_Small", "33", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(rx, BY + 14.0), nets={"1": "MIC_BCLK", "2": "MIC_BCLK_R"})  # fmt: skip
    d.add("R2", "Device:R_Small", "33", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(rx, BY + 16.0), nets={"1": "MIC_WS", "2": "MIC_WS_R"})  # fmt: skip
    d.add("C4", "Device:C_Small", "1u", "Capacitor_SMD:C_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(rx, BY + 18.0), nets={"1": "+3V3", "2": "GND"})  # fmt: skip
    # SD lines: 100k pull-down each, as the ICS-43434 datasheet asks for a tri-stated SD line.
    d.add("R3", "Device:R_Small", "100k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(rx, BY + 22.0), nets={"1": "MIC_SD0", "2": "GND"})  # fmt: skip
    d.add("R4", "Device:R_Small", "100k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(rx, BY + 24.0), nets={"1": "MIC_SD1", "2": "GND"})  # fmt: skip
    # MIC_LIVE: the bar drives it from the mics' own supply; low when the bar is unplugged or muted.
    d.add("R5", "Device:R_Small", "100k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(rx, BY + 26.0), nets={"1": "MIC_LIVE", "2": "GND"})  # fmt: skip

    # LEDs on the right edge: ACT from the CM5 (pin 21 sinks up to 20 mA), PWR from +5V.
    d.add("R7", "Device:R_Small", "1k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 58.0, BY + 31.0), nets={"1": "+3V3", "2": "LED_ACT_A"})  # fmt: skip
    d.add("D3", "Device:LED", "green ACT", "LED_SMD:LED_0603_1608Metric",
          sch_at=(0, 0), pcb_at=(BX + 58.0, BY + 33.0), pcb_rot=180,
          nets={"2": "LED_ACT_A", "1": "LED_nACT"})  # fmt: skip
    d.add("R6", "Device:R_Small", "2.2k", "Resistor_SMD:R_0402_1005Metric",
          sch_at=(0, 0), pcb_at=(BX + 58.0, BY + 36.0), nets={"1": "+5V", "2": "LED_PWR_A"})  # fmt: skip
    d.add("D2", "Device:LED", "green PWR", "LED_SMD:LED_0603_1608Metric",
          sch_at=(0, 0), pcb_at=(BX + 58.0, BY + 38.0), pcb_rot=180,
          nets={"2": "LED_PWR_A", "1": "GND"})  # fmt: skip
    d.add("SW1", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_TL3342",
          sch_at=(0, 0), pcb_at=(BX + 32.0, BY + 47.5), nets={"1": "nRPIBOOT", "2": "GND"})  # fmt: skip
    for i, at in enumerate(HOLES, start=1):
        d.add(f"H{i}", "Mechanical:MountingHole", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5",
              sch_at=(0, 0), pcb_at=at, nets={})  # fmt: skip

    for part in d.parts:  # 0402/0603 parts and holes: references on the fab layer only (README)
        if part.ref[0] in "RCDFH" or part.ref == "SW1":
            part.hide_ref = True
    for ref, (x, y, rot) in SCHEMATIC.items():
        part = next(p for p in d.parts if p.ref == ref)
        part.sch_at = (x, y)
        part.sch_rot = rot

    # Copper: In1.Cu is a solid ground plane, In2.Cu the +5V pour, both faces poured with GND.
    d.zone("GND", layers=("In1.Cu",), polygon=notched(0.3), connect="solid")
    d.zone("+5V", layers=("In2.Cu",), polygon=notched(0.3), connect="solid")
    d.zone("GND", layers=("F.Cu", "B.Cu"), polygon=notched(0.3), clearance=0.25, connect="solid")
    d.keepout(ANTENNA, layers=("F.Cu", "In1.Cu", "In2.Cu", "B.Cu"), name="antenna")

    d.tmds_report = route_tmds(d)
    # The GND pads between the TMDS pairs (outer row) join their inner-row twins straight across,
    # and a via above the inner pad takes both to the plane.
    for pin in (168, 174, 180, 186, 192):
        outer, inner = jpad(J2_AT, pin - 100), jpad(J2_AT, pin - 1 - 100)
        d.track("GND", [outer, inner], "F.Cu", width=0.2)
        d.via("GND", inner[0], round(inner[1] - 0.35 - 0.12 - 0.225, 3))
    # 3D bodies the library lacks (models/README.md): box approximations for the renders.
    for ref in ("J1", "J2"):
        d.model(ref, "${KIPRJMOD}/models/df40c_100ds.wrl", replace=True)
    d.model("J4", "${KIPRJMOD}/models/usb_c_hro_31m12.wrl", offset=(0.0, 0.6, 0.0), replace=True)
    tie_fine_pitch_grounds(d, ("J1", "J2", "J3"))
    d.stitch_pads("GND")

    d.text("AGENTCAST v0.1", BX + 33.0, BY + 51.0, "F.SilkS", 1.0, 0.15)
    d.text("BOOT", BX + 32.0, BY + 43.6, "F.SilkS", 0.8, 0.12)
    d.text("MIC", BX + 62.5, BY + 11.5, "F.SilkS", 0.8, 0.12)
    d.text("ACT", BX + 60.8, BY + 33.0, "F.SilkS", 0.8, 0.12)
    d.text("PWR", BX + 60.8, BY + 38.0, "F.SilkS", 0.8, 0.12)
    return d

