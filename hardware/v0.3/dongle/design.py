"""Agentcast dongle v0.3: a stick. One board, 67 x 46 mm, with the HDMI port at one end.

A Raspberry Pi CM5 carrier with HDMI out, an on-board mic, a USB-C host port for an external mic,
and a hardware mute. v0.2 was 57 x 50.4 mm with every port along one long edge; v0.3 turns the
layout so the board is long and narrow: the CM5's antenna at the far end, HDMI-A at the near end,
USB-C power on one long side and the USB-C host port on the other, both beside the HDMI port.

    workcenter design design.py --route     # from this folder

Board: 67 x 46 mm, 4 layers (F.Cu signal, In1.Cu GND plane, In2.Cu +5V plane, B.Cu signal). The CM5
(55 x 40 mm) is the width floor: the stick cannot be narrower than the module.

CM5 placement: two Hirose DF40C-100DS sockets centred 25.0 mm from the antenna edge and 3.0 mm in
from the long edges; M2.5 holes 3.5 mm in from each edge. Checked against Raspberry Pi's CM5 3D
model (RP-007222-DD-2, "rpi-cm5 3D_STEP"): the mating connectors 10164228-1001A1RLF sit at
(25.0, 3.0) and (25.0, 37.0) mm, the holes at (3.5|51.5, 3.5|36.5) mm, and the U.FL at
(2.567, 31.0) mm, which puts the antenna edge at x = 0 as in datasheet Figure 4. Which socket
carries pins 1-100 comes from Figure 4's labels; the 3D model has no pin numbers.

Mute (spec "Consent, privacy and trust"): SW2 feeds MIC_VDD from +3V3 in LIVE, and the red LED in
MUTE. MIC_VDD powers the mic, its clock buffers, the green LIVE LED, and the enable of the external
port's power switch U3. Muted, neither mic has power and no software can change it.

Area rules (P3 step 4):
- "antenna": x 100..109, y 105..126 on every layer. No track, no via; the pours are cut round it
  so no copper sits under the CM5's PCB antenna (CM5 datasheet section 2.2). Nothing is placed
  there, on either face.
- No other keep-out. F.Cu parts stay outside the CM5 outline (x 100..155, y 100..140) except the
  two sockets and the four holes: the 1.5 mm stacking height leaves no room under the module.
  B.Cu has no such limit.
"""

from __future__ import annotations

import csv
import itertools
import math
import os
import uuid
from pathlib import Path

import kicadgen

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / "library"

BX, BY = 100.0, 100.0  # board origin, top-left
W, H = 67.0, 46.0

J1_AT = (BX + 25.0, BY + 3.0)
J2_AT = (BX + 25.0, BY + 37.0)
HOLES = [(BX + 3.5, BY + 3.5), (BX + 51.5, BY + 3.5), (BX + 3.5, BY + 36.5), (BX + 51.5, BY + 36.5)]

# The near end (x = 67): HDMI-A opening out of the end, its "PCB Edge" mark (3.5 mm) on the edge.
# The USB-C receptacles (GCT USB4085, through-hole) open out of the long sides. Their footprint
# origin is pin A1; the body centre is 2.975 mm along x and the "PCB Edge" mark 6.1 mm along y.
HDMI_AT = (BX + 63.5, BY + 23.0)
USB_X = BX + 60.8  # body centre of both receptacles
USB_PWR_AT = (USB_X + 2.975, BY + 6.1)  # turned 180 degrees: opens out of the top side
USB_HOST_AT = (USB_X - 2.975, BY + H - 6.1)
# The strip below the module, at the far end: the mic, the LIVE / MUTED LEDs, the mute switch.
MIC_AT = (BX + 2.8, BY + 43.5)
MUTE_AT = (BX + 12.0, BY + 43.45)

ANTENNA = [(BX, BY + 5.0), (BX + 9.0, BY + 5.0), (BX + 9.0, BY + 26.0), (BX, BY + 26.0)]

# TMDS pairs: 100 ohm differential on F.Cu over the In1.Cu plane. JLC04161H-7628 stackup,
# prepreg 0.2104 mm, er 4.4: w 0.2 / s 0.2 gives 104 ohm (Hammerstad-Jensen, README).
PAIR_W, PAIR_S = 0.2, 0.2
HALF = (PAIR_W + PAIR_S) / 2  # trace centre from pair centre


def cm5_pins() -> dict[int, str]:
    with (LIB / "cm5_pins.csv").open(encoding="utf-8") as f:
        return {int(r["pin"]): r["signal"] for r in csv.DictReader(f)}


# CM5 pin -> net for every pin this board uses (pin plan in README). GND pins are added from the
# table. Every other pin is left open, as the datasheet allows (section 4.2).
CM5_NETS = {
    21: "LED_nACT",
    26: "I2S_WS",  # GPIO19, I2S0_WS (a2), into clock buffer U6
    27: "MIC_SD0",  # GPIO20, I2S0_SDI[0] (a2)
    30: "STATE_LED",  # GPIO6, output
    34: "MIC_LIVE",  # GPIO5, input
    49: "I2S_BCLK",  # GPIO18, I2S0_SCLK (a2), into clock buffer U5
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


def pad_at(d: kicadgen.Design, ref: str, number: str) -> tuple[float, float]:
    """Board position of a placed pad, read from the footprint."""
    box = next(b for b in d.pad_boxes() if b.ref == ref and b.number == number)
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


def chamfered(corners: list[tuple[float, float]], c: float) -> list[tuple[float, float]]:
    """A polyline through `corners` with each inner corner cut by a 45 degree chamfer of leg `c`."""
    out = [corners[0]]
    for a, b, n in zip(corners, corners[1:], corners[2:], strict=False):
        ux, uy = (b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b)
        vx, vy = (n[0] - b[0]) / math.dist(b, n), (n[1] - b[1]) / math.dist(b, n)
        out += [(b[0] - ux * c, b[1] - uy * c), (b[0] + vx * c, b[1] + vy * c)]
    return [*out, corners[-1]]


def offset(points: list[tuple[float, float]], o: float) -> list[tuple[float, float]]:
    """The polyline `points` moved sideways by `o` (positive to the left of the travel, as the board
    shows it), each corner the crossing of the two moved segments."""
    lines = []
    for a, b in itertools.pairwise(points):
        L = math.dist(a, b)
        nx, ny = (b[1] - a[1]) / L, -(b[0] - a[0]) / L  # left normal with y down
        lines.append(((a[0] + o * nx, a[1] + o * ny), (b[0] + o * nx, b[1] + o * ny)))
    out = [lines[0][0]]
    for (p1, p2), (q1, q2) in itertools.pairwise(lines):
        d1 = (p2[0] - p1[0], p2[1] - p1[1])
        d2 = (q2[0] - q1[0], q2[1] - q1[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        t = ((q1[0] - p1[0]) * d2[1] - (q1[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + t * d1[0], p1[1] + t * d1[1]))
    return [*out, lines[-1][1]]


def with_bumps(points: list, at_x: float, lane_y: float, depth: float, side: int, count: int) -> list:
    """Lengthen a trace by `count` V bumps of `depth` on its horizontal run at `lane_y`, starting
    at `at_x` and stepping right; `side` -1 bends up, +1 down (away from the partner trace)."""
    out = []
    for a, b in itertools.pairwise(points):
        out.append(a)
        if abs(a[1] - lane_y) < 1e-6 and abs(b[1] - lane_y) < 1e-6 and a[0] < at_x < b[0]:
            for k in range(count):
                x0 = at_x + k * 4 * depth
                out += [(x0, lane_y), (x0 + depth, lane_y + side * depth), (x0 + 2 * depth, lane_y)]
    out.append(points[-1])
    return [(round(x, 4), round(y, 4)) for x, y in out]


PAIRS = [  # name, CM5 P pin, CM5 N pin, HDMI + pin, HDMI - pin, lane y, riser x, bump x
    ("D2", 170, 172, 1, 3, BY + 40.1, BX + 45.0, BX + 37.0),
    ("D1", 176, 178, 4, 6, BY + 41.3, BX + 46.2, BX + 31.0),
    ("D0", 182, 184, 7, 9, BY + 42.5, BX + 47.4, BX + 27.0),
    ("CK", 188, 190, 10, 12, BY + 43.7, BX + 48.6, BX + 39.0),
]


def route_tmds(d: kicadgen.Design) -> list[str]:
    """Hand-route the four TMDS pairs on F.Cu; returns one report line per pair (README table).

    Each pair leaves J2's outer row downwards, runs along its own lane below the module, rises
    beside the HDMI receptacle and turns into its pins. The lanes nest: the right-most pair at J2
    (D2) takes the top lane and rises first, which is also the top pin pair of the receptacle."""
    report = []
    for name, cp, cn, hp, hn, lane, riser, bump_x in PAIRS:
        (xp0, y0), (xn0, _) = jpad(J2_AT, cp - 100), jpad(J2_AT, cn - 100)
        (xp1, yp1), (xn1, yn1) = pad_at(d, "J3", str(hp)), pad_at(d, "J3", str(hn))
        xc, yh = (xp0 + xn0) / 2, (yp1 + yn1) / 2
        split = xp1 - 1.9  # the pair splits here, ahead of the pins' shield pad between them
        centre = chamfered([(xc, y0), (xc, lane), (riser, lane), (riser, yh), (split, yh)], 0.6)
        p, n = offset(centre, HALF), offset(centre, -HALF)
        if p[0][0] < n[0][0]:  # P is the trace at J2's larger x
            p, n = n, p
        p[0], n[0] = (xp0, y0), (xn0, y0)
        p += [(split + 0.3, yp1), (xp1, yp1)]
        n += [(split + 0.3, yn1), (xn1, yn1)]
        skew = seg_len(p) - seg_len(n)
        if abs(skew) > 0.02:  # V bumps on the short trace's lane run, bending away from its partner
            depth = 0.2
            count = max(1, round(abs(skew) / ((2 * math.sqrt(2) - 2) * depth)))
            depth = round(abs(skew) / ((2 * math.sqrt(2) - 2) * count), 4)
            if skew > 0:
                n = with_bumps(n, bump_x, round(lane + HALF, 4), depth, +1, count)
            else:
                p = with_bumps(p, bump_x, round(lane - HALF, 4), depth, -1, count)
        p = [(round(x, 4), round(y, 4)) for x, y in p]
        n = [(round(x, 4), round(y, 4)) for x, y in n]
        d.track(f"HDMI_{name}_P", p, "F.Cu", width=PAIR_W)
        d.track(f"HDMI_{name}_N", n, "F.Cu", width=PAIR_W)
        report.append(
            f"{name}: P {seg_len(p):.3f} mm, N {seg_len(n):.3f} mm, skew {abs(seg_len(p) - seg_len(n)):.3f} mm"
        )
    return report


def tie_fine_pitch_grounds(d: kicadgen.Design, refs: dict[str, tuple[int, int]]) -> None:
    """A via and a short track for each GND pad of the fine-pitch connectors.

    At 0.4 mm and 0.5 mm pitch the face pour cannot reach a pad between other nets' pads, so a via
    beside it alone stays an island. The via goes off the pad's end, along the pad's long axis;
    `refs` names, per part, the direction tried first ((0, 1) down, (1, 0) right, (0, 0) away from
    the part's centre line), then the opposite one."""
    r, drill = d.via_size / 2, d.via_drill
    done = {(round(s[1][0], 3), round(s[1][1], 3)) for s in d.segments if s[0] == "GND"}
    for part in d.parts:
        if part.ref not in refs:
            continue
        for pad in [b for b in d.pad_boxes() if b.ref == part.ref and b.net == "GND" and b.kind == "smd"]:
            cx, cy = round((pad.x1 + pad.x2) / 2, 3), round((pad.y1 + pad.y2) / 2, 3)
            if (cx, cy) in done:
                continue  # already joined (the TMDS-side twins)
            tall = (pad.y2 - pad.y1) > (pad.x2 - pad.x1)
            first = refs[part.ref]
            if first == (0, 0):
                first = (0, 1 if cy > part.pcb_at[1] else -1) if tall else (1 if cx > part.pcb_at[0] else -1, 0)
            boxes = d.pad_boxes()
            for sx, sy in (first, (-first[0], -first[1])):
                vx = cx if sx == 0 else round((pad.x2 if sx > 0 else pad.x1) + sx * (0.12 + r), 3)
                vy = cy if sy == 0 else round((pad.y2 if sy > 0 else pad.y1) + sy * (0.12 + r), 3)
                if d._via_fits(vx, vy, r, drill, "GND", boxes):
                    d.track("GND", [(cx, cy), (vx, vy)], "F.Cu", width=0.2)
                    d.via("GND", vx, vy)
                    break


def build() -> kicadgen.Design:
    d = kicadgen.Design(name="agentcast_dongle", namespace=uuid.UUID("c4f0a7d3-2e6b-4b91-8d55-6a0e3f1b2c94"))
    d.copper_layers = 4
    d.plane_layers = ("In1.Cu", "In2.Cu")
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
            "nets": [f"HDMI_{p[0]}_{s}" for p in PAIRS for s in "PN"],
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
        *[f"HDMI_{p[0]}_{s}" for p in PAIRS for s in "PN"],
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

    def small(ref, sym, value, fp, at, nets, rot=0, layer="B.Cu"):
        d.add(ref, sym, value, fp, sch_at=(0, 0), pcb_at=(BX + at[0], BY + at[1]), pcb_rot=rot,
              pcb_layer=layer, nets=nets)  # fmt: skip

    R0402, C0402 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric"
    C0805, LED0603 = "Capacitor_SMD:C_0805_2012Metric", "LED_SMD:LED_0603_1608Metric"
    SOT235, SOT236 = "Package_TO_SOT_SMD:SOT-23-5", "Package_TO_SOT_SMD:SOT-23-6"
    USBC = "Connector_USB:USB_C_Receptacle_GCT_USB4085"

    # HDMI: the CM5's HDMI0, opening out of the near end. DDC, CEC and HPD are 5 V tolerant and go
    # straight to the connector.
    d.add(
        "J3",
        "Connector:HDMI_A",
        "10029449-001RLF",
        "Connector_Video:HDMI_A_Amphenol_10029449-x01xLF_Horizontal",
        sch_at=(0, 0),
        pcb_at=HDMI_AT,
        pcb_rot=90,
        nets={
            "1": "HDMI_D2_P", "3": "HDMI_D2_N", "4": "HDMI_D1_P", "6": "HDMI_D1_N",
            "7": "HDMI_D0_P", "9": "HDMI_D0_N", "10": "HDMI_CK_P", "12": "HDMI_CK_N",
            "2": "GND", "5": "GND", "8": "GND", "11": "GND", "17": "GND", "SH": "GND",
            "13": "HDMI_CEC", "15": "HDMI_SCL", "16": "HDMI_SDA", "18": "+5VP", "19": "HDMI_HPD",
        },
    )  # fmt: skip
    # HDMI +5V (pin 18): at least 55 mA (HDMI 1.4 section 4.2.7). TPS2051C: current limit, and
    # reverse-current blocking against a sink that drives its own 5 V (TPS2051C datasheet, features).
    small("U2", "Power_Management:TPS2051CDBV", "TPS2051CDBV", SOT235, (38.0, 27.0),
          {"5": "+5V", "4": "+3V3", "1": "+5VP", "2": "GND"})  # fmt: skip
    small("C3", "Device:C_Small", "100n", C0402, (41.5, 27.0), {"1": "+5VP", "2": "GND"}, rot=90)

    # USB-C power and rpiboot flashing (J4), out of the top long side. CC goes to the CM5, which
    # negotiates 5 V up to 5 A itself (CM5 datasheet section 2.12.1).
    d.add(
        "J4",
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "USB4085-GF-A",
        USBC,
        sch_at=(0, 0),
        pcb_at=USB_PWR_AT,
        pcb_rot=180,
        nets={
            "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
            "A4": "+5V", "A9": "+5V", "B4": "+5V", "B9": "+5V",
            "A5": "CC1", "B5": "CC2",
            "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
        },
    )  # fmt: skip
    small("U1", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", SOT236, (46.0, 8.0),
          {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "+5V"}, rot=90)  # fmt: skip
    small("C1", "Device:C_Small", "22u", C0805, (42.0, 8.0), {"1": "+5V", "2": "GND"}, rot=90)
    small("C2", "Device:C_Small", "22u", C0805, (38.5, 8.0), {"1": "+5V", "2": "GND"}, rot=90)

    # USB-C host port (J6) for an external USB mic, out of the bottom long side: the USB 2.0 pair of
    # the CM5's USB 3.0 port 0. U3 powers it only while MIC_VDD is up, so mute cuts it too.
    d.add(
        "J6",
        "Connector:USB_C_Receptacle_USB2.0_16P",
        "USB4085-GF-A",
        USBC,
        sch_at=(0, 0),
        pcb_at=USB_HOST_AT,
        nets={
            "A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
            "A4": "VBUS_HOST", "A9": "VBUS_HOST", "B4": "VBUS_HOST", "B9": "VBUS_HOST",
            "A5": "CC1_H", "B5": "CC2_H",
            "A6": "USB_H_DP", "B6": "USB_H_DP", "A7": "USB_H_DN", "B7": "USB_H_DN",
        },
    )  # fmt: skip
    small("U3", "Power_Management:TPS2051CDBV", "TPS2051CDBV", SOT235, (38.0, 31.0),
          {"5": "+5V", "4": "MIC_VDD", "1": "VBUS_HOST", "2": "GND"})  # fmt: skip
    small("C5", "Device:C_Small", "10u", C0805, (41.5, 31.0), {"1": "VBUS_HOST", "2": "GND"}, rot=90)
    # Rp 56k on each CC: a source offering default USB power (USB Type-C spec, Table 4-24).
    small("R8", "Device:R_Small", "56k", R0402, (34.5, 30.5), {"1": "VBUS_HOST", "2": "CC1_H"}, rot=90)
    small("R9", "Device:R_Small", "56k", R0402, (34.5, 33.0), {"1": "VBUS_HOST", "2": "CC2_H"}, rot=90)
    small("U4", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", SOT236, (40.0, 35.2),
          {"1": "USB_H_DP", "6": "USB_H_DP", "3": "USB_H_DN", "4": "USB_H_DN", "2": "GND", "5": "VBUS_HOST"},
          rot=90)  # fmt: skip

    # Mute switch in the strip below the module, actuator out of the bottom long side.
    d.add("SW2", "Switch:SW_SPDT", "PCM12SMTR", "Button_Switch_SMD:SW_SPDT_PCM12",
          sch_at=(0, 0), pcb_at=MUTE_AT, nets={"2": "+3V3", "1": "MIC_VDD", "3": "MUTED"})  # fmt: skip
    small("C10", "Device:C_Small", "10u", "Capacitor_SMD:C_0603_1608Metric", (24.0, 30.0),
          {"1": "MIC_VDD", "2": "GND"}, rot=90)  # fmt: skip
    # 100k bleeds MIC_VDD down when muted and holds U3's enable low.
    small("R11", "Device:R_Small", "100k", R0402, (25.7, 30.0), {"1": "MIC_VDD", "2": "GND"}, rot=90)
    small("R13", "Device:R_Small", "1k", R0402, (6.0, 42.5), {"1": "MIC_VDD", "2": "LED_LIVE_A"})
    small("D1", "Device:LED", "green LIVE", LED0603, (6.0, 42.5), {"2": "LED_LIVE_A", "1": "GND"},
          rot=180, layer="F.Cu")  # fmt: skip
    small("R14", "Device:R_Small", "1k", R0402, (6.0, 44.7), {"1": "MUTED", "2": "LED_MUTED_A"})
    small("D2", "Device:LED", "red MUTED", LED0603, (6.0, 44.7), {"2": "LED_MUTED_A", "1": "GND"},
          rot=180, layer="F.Cu")  # fmt: skip
    # MIC_LIVE tells the CM5 the mics have power: 10k from MIC_VDD into a 100k pull-down.
    small("R4", "Device:R_Small", "10k", R0402, (27.2, 30.0), {"1": "MIC_VDD", "2": "MIC_LIVE"}, rot=90)
    small("R5", "Device:R_Small", "100k", R0402, (28.7, 30.0), {"1": "MIC_LIVE", "2": "GND"}, rot=90)

    # On-board mic: ICS-43434, left channel of I2S0_SDI[0], at the far end. Its clocks come through
    # buffers on MIC_VDD (74LVC Ioff), so a muted mic gets no power through its clock pins.
    d.add("MK1", "Agentcast:ICS-43434_TS", "ICS-43434", "Sensor_Audio:InvenSense_ICS-43434-6_3.5x2.65mm",
          sch_at=(0, 0), pcb_at=MIC_AT,
          nets={"1": "MIC_WS", "2": "GND", "3": "GND", "4": "MIC_BCLK", "5": "MIC_VDD", "6": "MIC_SD0"})  # fmt: skip
    small("C6", "Device:C_Small", "100n", C0402, (2.8, 41.4), {"1": "MIC_VDD", "2": "GND"})
    sc70 = "Package_TO_SOT_SMD:SOT-353_SC-70-5"
    small("U5", "74xGxx:74LVC1G34", "74LVC1G34", sc70, (12.0, 30.0),
          {"2": "I2S_BCLK", "4": "BCLK_B", "3": "GND", "5": "MIC_VDD"})  # fmt: skip
    small("C7", "Device:C_Small", "100n", C0402, (12.0, 32.7), {"1": "MIC_VDD", "2": "GND"})
    small("R1", "Device:R_Small", "33", R0402, (12.0, 27.3), {"1": "BCLK_B", "2": "MIC_BCLK"})
    small("U6", "74xGxx:74LVC1G34", "74LVC1G34", sc70, (16.5, 30.0),
          {"2": "I2S_WS", "4": "WS_B", "3": "GND", "5": "MIC_VDD"})  # fmt: skip
    small("C8", "Device:C_Small", "100n", C0402, (16.5, 32.7), {"1": "MIC_VDD", "2": "GND"})
    small("R2", "Device:R_Small", "33", R0402, (16.5, 27.3), {"1": "WS_B", "2": "MIC_WS"})
    # SD: 100k pull-down for the tri-stated line (ICS-43434 datasheet).
    small("R3", "Device:R_Small", "100k", R0402, (20.5, 30.0), {"1": "MIC_SD0", "2": "GND"}, rot=90)
    small("C4", "Device:C_Small", "1u", C0402, (22.0, 30.0), {"1": "+3V3", "2": "GND"}, rot=90)

    # PWR / ACT (CM5 pin 21 sinks up to 20 mA) / STATE (GPIO6) LEDs, on the bottom face.
    for ref, rref, value, rval, x, a_net, k_net in (
        ("D5", "R6", "green PWR", "2.2k", 32.0, "+5V", "GND"),
        ("D4", "R7", "green ACT", "1k", 35.0, "+3V3", "LED_nACT"),
        ("D3", "R12", "amber STATE", "330", 38.0, "STATE_LED", "GND"),
    ):
        node = {"D5": "LED_PWR_A", "D4": "LED_ACT_A", "D3": "LED_STATE_A"}[ref]
        small(rref, "Device:R_Small", rval, R0402, (x, 23.0), {"1": a_net, "2": node}, rot=90)
        small(ref, "Device:LED", value, LED0603, (x, 20.0), {"2": node, "1": k_net}, rot=90)
    small("SW1", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_B3U-1000P", (12.0, 36.0),
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

    # Copper: In1.Cu is a solid ground plane and In2.Cu a solid +5V plane, neither routed through;
    # both faces poured with GND.
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
    # The DF40 sockets have no body in KiCad's 3D library: a box from wrlgen (models/README.md).
    for ref in ("J1", "J2"):
        d.model(ref, "${KIPRJMOD}/models/df40c_100ds.wrl", replace=True)
    # The CM5 itself, for assembly pictures only (AGENTCAST_ASSEMBLY=1, `make assembly`), from
    # Raspberry Pi's 3D model (`make cm5-model`; not kept in git). Its frame: y up, antenna edge at
    # x = 0, the module's underside at z = 0; it sits 1.5 mm above the board (the stack height).
    if os.environ.get("AGENTCAST_ASSEMBLY") == "1" and (HERE / "models" / "cm5.step").is_file():
        d.model("H1", "${KIPRJMOD}/models/cm5.step", offset=(-3.5, -36.5, 1.5))
    # USB_H_DP (J2 pad 34) and HDMI_SCL (J2 pad 100) sit above the TMDS lanes in J2's outer row and
    # the router finds no way out of them: a via just below each pad takes it to B.Cu.
    for net, pad in (("USB_H_DP", 34), ("HDMI_SCL", 100)):
        x, y = jpad(J2_AT, pad)
        d.track(net, [(x, y), (x, round(y + 0.79, 3))], "F.Cu", width=0.15)
        d.via(net, x, round(y + 0.79, 3))
    # The CM5's six 5V pins (77-87, J1's outer row) join on a bar in the gap between the rows, and
    # three vias there take them to the +5V plane.
    fives = [jpad(J1_AT, n) for n in (77, 79, 81, 83, 85, 87)]
    bar_y = round(fives[0][1] + 0.84, 3)
    for x, y in fives:
        d.track("+5V", [(x, y), (x, bar_y)], "F.Cu", width=0.2)
    d.track("+5V", [(fives[-1][0], bar_y), (fives[0][0], bar_y)], "F.Cu", width=0.3)
    for x in (fives[-1][0] + 0.2, fives[2][0] - 0.2, fives[0][0]):
        d.track("+5V", [(round(x, 3), bar_y), (round(x, 3), round(bar_y + 0.7, 3))], "F.Cu", width=0.3)
        d.via("+5V", round(x, 3), round(bar_y + 0.7, 3))
    # HDMI_SCL: from the via under J2 pad 100, hand-routed on B.Cu up between SW1 and U6, across at
    # y 116 (clear of the bottom-face parts), down beside the receptacle, and through a second via
    # onto J3 pin 15. The router finds no path this long; this one leaves the way to J6 open.
    sx, sy = jpad(J2_AT, 100)
    sy = round(sy + 0.79, 3)
    hx, hy = pad_at(d, "J3", "15")
    d.track("HDMI_SCL", [(sx, sy), (BX + 14.7, sy - 0.5), (BX + 14.7, BY + 16.0), (hx - 2.5, BY + 16.0),
                         (hx - 2.5, hy)], "B.Cu", width=0.15)
    d.via("HDMI_SCL", hx - 2.5, hy)
    d.track("HDMI_SCL", [(hx - 2.5, hy), (hx, hy)], "F.Cu", width=0.15)
    # Bottom-face power pins get a via of their own to their plane, placed before routing: +5V into
    # U2 and U3, and U4's ground, which the routed tracks otherwise cut off from the B.Cu pour.
    for net, ref, pin in (("+5V", "U2", "5"), ("+5V", "U3", "5"), ("GND", "U4", "2")):
        px, py = pad_at(d, ref, pin)
        boxes = d.pad_boxes()
        for vx, vy in ((px, py - 1.15), (px, py + 1.15), (px - 1.0, py), (px + 1.0, py)):
            if d._via_fits(vx, vy, d.via_size / 2, d.via_drill, net, boxes):
                d.track(net, [(px, py), (round(vx, 3), round(vy, 3))], "B.Cu", width=0.3)
                d.via(net, round(vx, 3), round(vy, 3))
                break
    tie_fine_pitch_grounds(d, {"J1": (0, 0), "J2": (0, 0), "J3": (1, 0)})
    d.stitch_pads("GND")

    d.text("AGENTCAST v0.3", BX + 30.0, BY + 14.0, "B.SilkS", 1.0, 0.15)
    d.text("PWR", USB_X, BY + 10.6, "F.SilkS", 0.8, 0.12)
    d.text("USB", USB_X, BY + 35.4, "F.SilkS", 0.8, 0.12)
    d.text("MUTE", MUTE_AT[0], BY + 41.6, "B.SilkS", 0.8, 0.12)
    d.text("BOOT", BX + 12.0, BY + 38.6, "B.SilkS", 0.8, 0.12)
    return d
