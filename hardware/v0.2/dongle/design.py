"""Agentcast dongle v0.2: one board. A Raspberry Pi CM5 carrier with HDMI out, an on-board mic,
a USB-C host port for an external mic, and a hardware mute.

    workcenter design design.py --route     # from this folder

Board: 57 x 50.4 mm, 4 layers (F.Cu signal, In1.Cu GND plane, In2.Cu +5V pour, B.Cu signal).
The CM5 (55 x 40 mm) sits on two Hirose DF40C-100DS sockets with its antenna edge on the board's
left edge. Positions of the sockets and holes come from CM5 datasheet Figure 4 (section 4.1.1).
Along the bottom edge, on F.Cu: the mic, the HDMI-A receptacle, USB-C power (J4), USB-C host
(J6) and the mute switch. The small parts sit on B.Cu, under the module.

Mute (spec "Consent, privacy and trust"): SW2 feeds MIC_VDD from +3V3 in LIVE, and the red LED
in MUTE. MIC_VDD powers the mic, its clock buffers, the green LIVE LED, and the enable of the
external port's power switch U3. Muted, neither mic has power and no software can change it.

Area rules (P3 step 4):
- "antenna": x 100..109, y 105..126 on every layer. No track, no via; the pours are cut round it
  so no copper sits under the CM5's PCB antenna (CM5 datasheet section 2.2: keep the antenna away
  from ground planes). Nothing is placed there, on either face.
- No other keep-out. F.Cu parts stay outside the CM5 outline (x 100..155, y 100..140) except the
  two sockets and the four holes: the 1.5 mm stacking height leaves no room under the module.
  B.Cu has no such limit.
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
W, H = 57.0, 50.4

# CM5 placement (datasheet Figure 4): connectors centred 25.0 mm from the antenna edge, 3.0 mm
# in from the long edges; M2.5 holes 3.5 mm in from each edge.
J1_AT = (BX + 25.0, BY + 3.0)
J2_AT = (BX + 25.0, BY + 37.0)
HOLES = [(BX + 3.5, BY + 3.5), (BX + 51.5, BY + 3.5), (BX + 3.5, BY + 36.5), (BX + 51.5, BY + 36.5)]

# Bottom edge, F.Cu. The HDMI receptacle's "PCB Edge" mark (3.5 mm) and the USB-C receptacles'
# fronts (3.25 mm, as in v0.1) land on the board edge.
HDMI_AT = (BX + 17.2, BY + H - 3.5)
USB_PWR_AT = (BX + 32.0, BY + H - 3.25)
USB_HOST_AT = (BX + 43.0, BY + H - 3.25)
MUTE_AT = (BX + 53.4, BY + 45.5)
MIC_AT = (BX + 3.5, BY + 45.5)

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
    134: "USB_H_DP",  # USB 3.0 port 0, its USB 2.0 pair: the external mic
    136: "USB_H_DN",
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

# Schematic layout (P24): ref -> (x, y, angle), 2.54 mm steps on an A2 sheet. Blocks: power and
# flashing left, the CM5 centre, HDMI top right, the mic and mute right, the external port bottom
# right, LEDs and the boot button bottom left.
SCHEMATIC = {
    "J4": (50.8, 76.2, 0),
    "U1": (50.8, 132.08, 0),
    "C1": (81.28, 60.96, 0),
    "C2": (91.44, 60.96, 0),
    "J1": (162.56, 203.2, 0),
    "J2": (279.4, 203.2, 0),
    "J3": (403.86, 101.6, 0),
    "U2": (345.44, 50.8, 0),
    "C3": (370.84, 60.96, 0),
    "SW2": (342.9, 152.4, 0),
    "C10": (365.76, 170.18, 0),
    "R11": (375.92, 170.18, 0),
    "R13": (386.08, 167.64, 0),
    "D1": (386.08, 182.88, 270),
    "R14": (360.68, 193.04, 0),
    "D2": (360.68, 208.28, 270),
    "R4": (398.78, 167.64, 0),
    "R5": (398.78, 190.5, 0),
    "U5": (440.69, 167.64, 0),
    "C7": (424.18, 185.42, 0),
    "R1": (467.36, 167.64, 90),
    "U6": (440.69, 210.82, 0),
    "C8": (424.18, 228.6, 0),
    "R2": (467.36, 210.82, 90),
    "MK1": (523.24, 185.42, 0),
    "C6": (546.1, 172.72, 0),
    "R3": (508.0, 223.52, 0),
    "C4": (431.8, 139.7, 0),
    "J6": (520.7, 312.42, 0),
    "U3": (459.74, 271.78, 0),
    "C5": (485.14, 284.48, 0),
    "R8": (490.22, 330.2, 0),
    "R9": (500.38, 330.2, 0),
    "U4": (464.82, 340.36, 0),
    "SW1": (93.98, 304.8, 90),
    "R6": (93.98, 345.44, 0),
    "D5": (93.98, 365.76, 270),
    "R7": (124.46, 345.44, 0),
    "D4": (124.46, 365.76, 270),
    "R12": (154.94, 345.44, 0),
    "D3": (154.94, 365.76, 270),
    "H1": (520.7, 381.0, 0),
    "H2": (533.4, 381.0, 0),
    "H3": (546.1, 381.0, 0),
    "H4": (558.8, 381.0, 0),
}


def jpad(at: tuple[float, float], pad: int) -> tuple[float, float]:
    """Board position of DF40C-100DS pad `pad` for a socket placed at `at`, rotated 180 degrees.

    The library footprint has pad 1 at (-9.8, 1.54), odd pads on +y, 0.4 mm along x per pad pair.
    """
    fx = -9.8 + 0.4 * ((pad - 1) // 2)
    fy = 1.54 if pad % 2 else -1.54
    return (round(at[0] - fx, 3), round(at[1] - fy, 3))


def hpad(d: kicadgen.Design, pin: int) -> tuple[float, float]:
    """Board position of J3's pad `pin`, read from the placed footprint."""
    box = next(b for b in d.pad_boxes() if b.ref == "J3" and b.number == str(pin))
    return (round((box.x1 + box.x2) / 2, 3), round((box.y1 + box.y2) / 2, 3))


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
        (xp1, y1), (xn1, _) = hpad(d, hp), hpad(d, hn)
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
    d = kicadgen.Design(name="agentcast_dongle", namespace=uuid.UUID("7e3a51c2-0b9d-4f6e-a2c8-91d4e5f60a72"))
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
    d.power_nets = {"GND": "GND", "+5V": "+5V", "+3V3": "+3V3", "+5VP": "+5VP", "MIC_VDD": "VDD"}
    d.flagged_nets = ["GND", "+5V", "+3V3", "MIC_VDD"]  # +5VP is driven by U2's output
    d.check_pulls = True
    d.defined_nets = {
        "nRPIBOOT": "CM5 pin 93: internal 10k pull-up to CM5_3.3V (CM5 datasheet section 4.2)",
        "HDMI_SDA": "CM5 pin 199: internal 1.8k pull-up (CM5 datasheet section 4.2)",
        "HDMI_SCL": "CM5 pin 200: internal 1.8k pull-up (CM5 datasheet section 4.2)",
        "MIC_BCLK": "driven by U5's output through the 33 ohm series resistor R1",
        "MIC_WS": "driven by U6's output through the 33 ohm series resistor R2",
        "MUTED": "held low through R14 and D2 to GND while SW2 is in LIVE",
        "I2S_BCLK": "driven by the CM5's I2S0_SCLK (GPIO18); U5 has Ioff while MIC_VDD is off",
        "I2S_WS": "driven by the CM5's I2S0_WS (GPIO19); U6 has Ioff while MIC_VDD is off",
    }
    # Labels for the nets that cross the sheet between the CM5 sockets and the other blocks.
    d.sch_label_nets = (
        "CC1", "CC2", "USB_DP", "USB_DN", "USB_H_DP", "USB_H_DN", "nRPIBOOT", "LED_nACT",
        "I2S_BCLK", "I2S_WS", "MIC_SD0", "MIC_LIVE", "STATE_LED",
        "HDMI_CEC", "HDMI_HPD", "HDMI_SDA", "HDMI_SCL",
        *[f"HDMI_{p}_{s}" for p, *_ in PAIRS for s in "PN"],
    )  # fmt: skip

    table = cm5_pins()
    nets_of = dict(CM5_NETS)
    nets_of[26], nets_of[49] = "I2S_WS", "I2S_BCLK"  # GPIO19, GPIO18: into the clock buffers
    sockets = (("J1", "CM5_J1", 1, J1_AT), ("J2", "CM5_J2", 101, J2_AT))
    for ref, sym, first, at in sockets:
        nets = {}
        for pin in range(first, first + 100):
            net = "GND" if table[pin] == "GND" else nets_of.get(pin)
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

    def small(ref, sym, value, fp, at, nets, rot=0, layer="B.Cu"):
        d.add(ref, sym, value, fp, sch_at=(0, 0), pcb_at=(BX + at[0], BY + at[1]), pcb_rot=rot,
              pcb_layer=layer, nets=nets)  # fmt: skip

    R0402, C0402 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric"
    C0805, LED0603 = "Capacitor_SMD:C_0805_2012Metric", "LED_SMD:LED_0603_1608Metric"
    SOT235 = "Package_TO_SOT_SMD:SOT-23-5"

    # HDMI: the CM5's HDMI0. DDC, CEC and HPD are 5 V tolerant and go straight to the connector.
    d.add(
        "J3",
        "Connector:HDMI_A",
        "10029449-001RLF",
        "Connector_Video:HDMI_A_Amphenol_10029449-x01xLF_Horizontal",
        sch_at=(0, 0),
        pcb_at=HDMI_AT,
        nets={
            "1": "HDMI_D2_P", "3": "HDMI_D2_N", "4": "HDMI_D1_P", "6": "HDMI_D1_N",
            "7": "HDMI_D0_P", "9": "HDMI_D0_N", "10": "HDMI_CK_P", "12": "HDMI_CK_N",
            "2": "GND", "5": "GND", "8": "GND", "11": "GND", "17": "GND", "SH": "GND",
            "13": "HDMI_CEC", "15": "HDMI_SCL", "16": "HDMI_SDA", "18": "+5VP", "19": "HDMI_HPD",
        },
    )  # fmt: skip
    # HDMI +5V (pin 18): at least 55 mA (HDMI 1.4 section 4.2.7). TPS2051C: current limit, and
    # reverse-current blocking against a sink that drives its own 5 V (TPS2051C datasheet, features).
    small("U2", "Power_Management:TPS2051CDBV", "TPS2051CDBV", SOT235, (14.0, 33.0),
          {"5": "+5V", "4": "+3V3", "1": "+5VP", "2": "GND"})  # fmt: skip
    small("C3", "Device:C_Small", "100n", C0402, (17.5, 33.0), {"1": "+5VP", "2": "GND"}, rot=90)

    # USB-C power and rpiboot flashing (J4). CC goes to the CM5, which negotiates 5 V up to 5 A
    # itself (CM5 datasheet section 2.12.1).
    d.add(
        "J4",
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "TYPE-C-31-M-12",
        "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        sch_at=(0, 0),
        pcb_at=USB_PWR_AT,
        nets={
            "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
            "A4": "+5V", "A9": "+5V", "B4": "+5V", "B9": "+5V",
            "A5": "CC1", "B5": "CC2",
            "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
        },
    )  # fmt: skip
    small("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (31.0, 33.0),
          {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "+5V"}, rot=90)  # fmt: skip
    small("C1", "Device:C_Small", "22u", C0805, (27.0, 31.0), {"1": "+5V", "2": "GND"}, rot=90)
    small("C2", "Device:C_Small", "22u", C0805, (35.0, 31.0), {"1": "+5V", "2": "GND"}, rot=90)

    # USB-C host port (J6) for an external USB mic: the USB 2.0 pair of the CM5's USB 3.0 port 0.
    # U3 powers it only while MIC_VDD is up, so the mute switch cuts the external mic too.
    d.add(
        "J6",
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "TYPE-C-31-M-12",
        "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        sch_at=(0, 0),
        pcb_at=USB_HOST_AT,
        nets={
            "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
            "A4": "VBUS_HOST", "A9": "VBUS_HOST", "B4": "VBUS_HOST", "B9": "VBUS_HOST",
            "A5": "CC1_H", "B5": "CC2_H",
            "A6": "USB_H_DP", "B6": "USB_H_DP", "A7": "USB_H_DN", "B7": "USB_H_DN",
        },
    )  # fmt: skip
    small("U3", "Power_Management:TPS2051CDBV", "TPS2051CDBV", SOT235, (47.0, 29.0),
          {"5": "+5V", "4": "MIC_VDD", "1": "VBUS_HOST", "2": "GND"})  # fmt: skip
    small("C5", "Device:C_Small", "10u", C0805, (51.0, 29.0), {"1": "VBUS_HOST", "2": "GND"}, rot=90)
    # Rp 56k on each CC: a source offering default USB power (USB Type-C spec, Table 4-24).
    small("R8", "Device:R_Small", "56k", R0402, (39.5, 29.0), {"1": "VBUS_HOST", "2": "CC1_H"}, rot=90)
    small("R9", "Device:R_Small", "56k", R0402, (41.0, 29.0), {"1": "VBUS_HOST", "2": "CC2_H"}, rot=90)
    small("U4", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", (43.0, 33.0),
          {"1": "USB_H_DP", "6": "USB_H_DP", "3": "USB_H_DN", "4": "USB_H_DN", "2": "GND", "5": "VBUS_HOST"},
          rot=90)  # fmt: skip

    # Mute switch, right edge, actuator out of the edge.
    d.add("SW2", "Switch:SW_SPDT", "PCM12SMTR", "Button_Switch_SMD:SW_SPDT_PCM12",
          sch_at=(0, 0), pcb_at=MUTE_AT, pcb_rot=90, nets={"2": "+3V3", "1": "MIC_VDD", "3": "MUTED"})  # fmt: skip
    small("C10", "Device:C_Small", "10u", "Capacitor_SMD:C_0603_1608Metric", (53.0, 33.0),
          {"1": "MIC_VDD", "2": "GND"}, rot=90)  # fmt: skip
    # 100k bleeds MIC_VDD down when muted and holds U3's enable low.
    small("R11", "Device:R_Small", "100k", R0402, (55.0, 33.0), {"1": "MIC_VDD", "2": "GND"}, rot=90)
    small("R13", "Device:R_Small", "1k", R0402, (49.6, 42.5), {"1": "MIC_VDD", "2": "LED_LIVE_A"}, rot=90)
    small("D1", "Device:LED", "green LIVE", LED0603, (49.6, 42.5), {"2": "LED_LIVE_A", "1": "GND"},
          rot=90, layer="F.Cu")  # fmt: skip
    small("R14", "Device:R_Small", "1k", R0402, (49.6, 46.5), {"1": "MUTED", "2": "LED_MUTED_A"}, rot=90)
    small("D2", "Device:LED", "red MUTED", LED0603, (49.6, 46.5), {"2": "LED_MUTED_A", "1": "GND"},
          rot=90, layer="F.Cu")  # fmt: skip
    # MIC_LIVE tells the CM5 the mics have power: 10k from MIC_VDD into a 100k pull-down.
    small("R4", "Device:R_Small", "10k", R0402, (24.0, 20.0), {"1": "MIC_VDD", "2": "MIC_LIVE"}, rot=90)
    small("R5", "Device:R_Small", "100k", R0402, (25.5, 20.0), {"1": "MIC_LIVE", "2": "GND"}, rot=90)

    # On-board mic: ICS-43434, left channel of I2S0_SDI[0]. Its clocks come through buffers on
    # MIC_VDD (74LVC Ioff), so a muted mic gets no power through its clock pins.
    d.add("MK1", "Agentcast:ICS-43434_TS", "ICS-43434", "Sensor_Audio:InvenSense_ICS-43434-6_3.5x2.65mm",
          sch_at=(0, 0), pcb_at=MIC_AT,
          nets={"1": "MIC_WS", "2": "GND", "3": "GND", "4": "MIC_BCLK", "5": "MIC_VDD", "6": "MIC_SD0"})  # fmt: skip
    small("C6", "Device:C_Small", "100n", C0402, (3.5, 42.6), {"1": "MIC_VDD", "2": "GND"})
    small("U5", "74xGxx:74LVC1G34", "74LVC1G34", "Package_TO_SOT_SMD:SOT-353_SC-70-5", (13.0, 23.0),
          {"2": "I2S_BCLK", "4": "BCLK_B", "3": "GND", "5": "MIC_VDD"})  # fmt: skip
    small("C7", "Device:C_Small", "100n", C0402, (13.0, 25.5), {"1": "MIC_VDD", "2": "GND"})
    small("R1", "Device:R_Small", "33", R0402, (13.0, 20.5), {"1": "BCLK_B", "2": "MIC_BCLK"})
    small("U6", "74xGxx:74LVC1G34", "74LVC1G34", "Package_TO_SOT_SMD:SOT-353_SC-70-5", (17.5, 23.0),
          {"2": "I2S_WS", "4": "WS_B", "3": "GND", "5": "MIC_VDD"})  # fmt: skip
    small("C8", "Device:C_Small", "100n", C0402, (17.5, 25.5), {"1": "MIC_VDD", "2": "GND"})
    small("R2", "Device:R_Small", "33", R0402, (17.5, 20.5), {"1": "WS_B", "2": "MIC_WS"})
    # SD: 100k pull-down for the tri-stated line (ICS-43434 datasheet).
    small("R3", "Device:R_Small", "100k", R0402, (21.0, 23.0), {"1": "MIC_SD0", "2": "GND"}, rot=90)
    small("C4", "Device:C_Small", "1u", C0402, (22.5, 23.0), {"1": "+3V3", "2": "GND"}, rot=90)

    # LEDs on the bottom strip, left: PWR, ACT (CM5 pin 21 sinks up to 20 mA), STATE (GPIO6).
    small("R6", "Device:R_Small", "2.2k", R0402, (6.6, 41.8), {"1": "+5V", "2": "LED_PWR_A"}, rot=90)
    small("D5", "Device:LED", "green PWR", LED0603, (6.6, 41.8), {"2": "LED_PWR_A", "1": "GND"},
          rot=90, layer="F.Cu")  # fmt: skip
    small("R7", "Device:R_Small", "1k", R0402, (6.6, 45.0), {"1": "+3V3", "2": "LED_ACT_A"}, rot=90)
    small("D4", "Device:LED", "green ACT", LED0603, (6.6, 45.0), {"2": "LED_ACT_A", "1": "LED_nACT"},
          rot=90, layer="F.Cu")  # fmt: skip
    small("R12", "Device:R_Small", "330", R0402, (6.6, 48.2), {"1": "STATE_LED", "2": "LED_STATE_A"}, rot=90)
    small("D3", "Device:LED", "amber STATE", LED0603, (6.6, 48.2), {"2": "LED_STATE_A", "1": "GND"},
          rot=90, layer="F.Cu")  # fmt: skip
    small("SW1", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_B3U-1000P", (4.0, 32.0),
          {"1": "nRPIBOOT", "2": "GND"})  # fmt: skip
    for i, at in enumerate(HOLES, start=1):
        d.add(f"H{i}", "Mechanical:MountingHole", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5",
              sch_at=(0, 0), pcb_at=at, nets={})  # fmt: skip

    for part in d.parts:  # small parts and holes: references on the fab layer only (README)
        if part.ref[0] in "RCDH" or part.ref in ("SW1", "SW2", "J4", "J6", "U1", "U2", "U3", "U4", "U5", "U6"):
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
    for ref in ("J4", "J6"):
        d.model(ref, "${KIPRJMOD}/models/usb_c_hro_31m12.wrl", offset=(0.0, 0.6, 0.0), replace=True)
    tie_fine_pitch_grounds(d, ("J1", "J2", "J3"))
    d.stitch_pads("GND")

    d.text("AGENTCAST v0.2", BX + 28.0, BY + 3.0 + 40.0 - 1.5, "B.SilkS", 1.0, 0.15)
    d.text("PWR", USB_PWR_AT[0], BY + 41.2, "F.SilkS", 0.8, 0.12)
    d.text("USB", USB_HOST_AT[0], BY + 41.2, "F.SilkS", 0.8, 0.12)
    d.text("MUTE", BX + 53.4, BY + 40.6, "F.SilkS", 0.8, 0.12)
    d.text("BOOT", BX + 4.0, BY + 29.6, "B.SilkS", 0.8, 0.12)
    return d
