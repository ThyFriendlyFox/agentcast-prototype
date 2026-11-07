"""Agentcast dongle v0.5: our own small computer on an 80 x 30 mm stick with a male HDMI plug.

v0.1-v0.4 carried a Raspberry Pi CM5 (55 x 40 mm), which set the stick's width. The dongle does
not need Linux: it streams the room's audio to the cloud agent, shows what the cloud renders on the
TV, and plays the agent's voice. v0.5 does that with:

- ESP32-P4NRW32 (U1): dual RISC-V 400 MHz, 32 MB PSRAM in the package, MIPI DSI, I2S, USB 2.0 HS.
- LT8912B (U3): MIPI DSI (2 lanes, 1.5 Gb/s each) to HDMI, with I2S audio into the HDMI stream.
- ESP32-C6-MINI-1 (U2): Wi-Fi 6, on SDIO to the P4 (Espressif's ESP-Hosted).
- XUNPU HDMI-003 male HDMI plug (J3 top contacts, J3B bottom contacts) on the board's end.
- ICS-43434 I2S mic, its clocks shared with the LT8912B's audio: capture and playback run on one
  clock, which the echo canceller needs.
- USB-C power and flashing (J4, the P4's USB serial/JTAG), USB-C host port for an external mic (J6,
  the P4's USB 2.0 HS OTG), the hardware mute (SW2) that powers both mics.

    workcenter design design.py --route     # from this folder

Board: 80 x 30 mm, 8 layers (F.Cu signal, In1.Cu GND plane, In2.Cu to In5.Cu signal, In6.Cu GND
plane, B.Cu signal), 1.6 mm, JLCPCB's JLC081611-2116 stackup
(the plug clamps 1.60 mm). Two 0.6 x 0.8 mm slots in the plug end take the plug's
shell (XUNPU drawing); the outline is drawn by StickDesign below.

Voltage domains: +5V (USB-C), +3V3 (P4 IO banks 0/4/5 and LP, C6, USB), VDD_HP (P4 core, ~1.1 V from
U5 under the P4's own control, Espressif hardware design guidelines Fig. 5), +1V8 (LT8912B and P4
IO bank 6, GPIO49-54, which talks to it: the LT8912B's I2C and I2S pins are 1.8 V CMOS, LT8912B
datasheet Table 6.2.1), MIC_3V3 / MIC_1V8 (switched by the mute switch).

Area rules (P3 step 4):
- "antenna": x 100..106.5, the full width, every layer. The C6 module's PCB antenna overhangs it;
  no copper under it (ESP32-C6-MINI-1 datasheet, antenna keepout). Nothing is placed there.
- No other keep-out. Parts sit on both faces.
"""

from __future__ import annotations

import csv
import heapq
import itertools
import json
import math
import os
import uuid
from pathlib import Path

import kicadgen

HERE = Path(__file__).resolve().parent
LIB = HERE.parent / "library"

BX, BY = 100.0, 100.0  # board origin, top-left
W, H = 80.0, 30.0  # length (x, the plug at x = W), width (y)
Y0 = 2.0  # the layout's frame sits Y0 below the top edge: the board grew 2 mm on each long side
CY = BY + H / 2  # the stick's centre line

PLUG_AT = (BX + W, CY)
SLOT_X = 6.80  # the plug's shell slots, either side of the centre line (XUNPU drawing)
SLOT_W, SLOT_D = 0.60, 0.80

C6_AT = (BX + 11.5, CY)  # module turned 90 degrees: its antenna end over x 100.5..106
P4_AT = (BX + 44.0, CY)  # 8 mm right of v0.5's first layout: the mic moved to the P4's left
LT_AT = (BX + 65.5, CY)
USB_X = BX + 23.5  # body centre of both USB-C receptacles
USB_PWR_AT = (USB_X + 2.975, BY + 6.1)  # GCT USB4085, origin at A1; turned 180: opens out of y = 0
USB_HOST_AT = (USB_X - 2.975, BY + H - 6.1)  # opens out of y = H
MUTE_AT = (BX + 52.0, BY + H - 2.55)
MIC_AT = (BX + 33.0, BY + Y0 + 23.5)

ANTENNA = [(BX, BY), (BX + 6.5, BY), (BX + 6.5, BY + H), (BX, BY + H)]

PAIR_W, PAIR_S = 0.12, 0.16  # 100 ohm differential on F.Cu over In1.Cu, 0.109 mm of 2116 prepreg (README)
HALF = (PAIR_W + PAIR_S) / 2


class StickDesign(kicadgen.Design):
    """A Design whose plug end (x2) has the two shell slots cut into it."""

    def _edge_cuts(self, ns: uuid.UUID) -> list:
        items = super()._edge_cuts(ns)
        _, _, x2, _ = self.outline
        right = next(
            i for i, it in enumerate(items)
            if it[0] == "gr_line" and float(it[1][1]) == x2 and float(it[2][1]) == x2
        )  # fmt: skip
        ya, yb = float(items[right][1][2]), float(items[right][2][2])
        lo, hi = min(ya, yb), max(ya, yb)
        cuts = sorted((CY + s * SLOT_X - SLOT_W / 2, CY + s * SLOT_X + SLOT_W / 2) for s in (-1, 1))
        pts = [lo]
        for a, b in cuts:
            pts += [a, b]
        pts.append(hi)
        segs = []
        for k, (a, b) in enumerate(itertools.pairwise(pts)):
            if k % 2 == 0:  # board edge between slots
                segs.append(((x2, a), (x2, b)))
        for a, b in cuts:  # each slot: in, across, out
            segs += [((x2, a), (x2 - SLOT_D, a)), ((x2 - SLOT_D, a), (x2 - SLOT_D, b)), ((x2 - SLOT_D, b), (x2, b))]

        def line(k, s, e):
            return [
                "gr_line",
                ["start", kicadgen.fmt(s[0]), kicadgen.fmt(s[1])],
                ["end", kicadgen.fmt(e[0]), kicadgen.fmt(e[1])],
                ["stroke", ["width", "0.1"], ["type", "default"]],
                ["layer", kicadgen.Q("Edge.Cuts")],
                ["uuid", kicadgen.uid(ns, f"edge/slot/{k}")],
            ]

        return items[:right] + [line(k, s, e) for k, (s, e) in enumerate(segs)] + items[right + 1 :]


def table(name: str) -> dict[int, str]:
    with (LIB / name).open(encoding="utf-8") as f:
        return {int(r["pin"]): r["name"] for r in csv.DictReader(f)}


# ESP32-P4 pin -> net (pin plan, README). Unlisted GPIOs are left open.
P4_NETS = {
    9: "+3V3", 21: "+3V3", 62: "+3V3", 85: "+3V3", 51: "+3V3", 75: "+3V3", 77: "+3V3", 101: "+3V3", 102: "+3V3",
    96: "+1V8",  # VDD_IO_6: GPIO49-54 at 1.8 V for the LT8912B and the mic
    26: "VDD_HP", 54: "VDD_HP", 76: "VDD_HP", 91: "VDD_HP",
    30: "VDDO_FLASH", 71: "VDDO_FLASH",  # flash LDO out (3.3 V default) -> flash IO and flash VCC
    59: "VDDO_PSRAM", 67: "VDDO_PSRAM", 72: "VDDO_PSRAM",  # PSRAM LDO out -> in-package PSRAM IO
    73: "VDD_MIPI", 41: "VDD_MIPI",  # VDDO_3 set to 2.5 V in firmware -> MIPI D-PHY (HDG 1.3.2)
    74: "VDDO_4",
    78: "FB_DCDC", 79: "EN_DCDC", 99: "XTAL_N", 100: "XTAL_P", 103: "CHIP_PU",
    27: "FLASH_CS", 28: "FLASH_Q", 29: "FLASH_WP", 31: "FLASH_HOLD", 32: "FLASH_CK", 33: "FLASH_D",
    34: "DSI_REXT", 35: "DSI_D1_P", 36: "DSI_D1_N", 37: "DSI_CK_N", 38: "DSI_CK_P", 39: "DSI_D0_P", 40: "DSI_D0_N",
    49: "USB_HS_DN", 50: "USB_HS_DP",
    17: "C6_EN",  # GPIO16, open drain
    18: "LT_RST_N",  # GPIO17, open drain, pulled to +1V8
    19: "SDIO_CLK", 20: "SDIO_CMD", 22: "SDIO_D0", 23: "SDIO_D1", 24: "SDIO_D2", 25: "SDIO_D3",  # GPIO18-23
    52: "USB_FS_DN", 53: "USB_FS_DP",  # GPIO24/25: USB serial/JTAG
    66: "BOOT",  # GPIO35 strapping: low at reset = download mode
    68: "GPIO36_PU",  # GPIO36 strapping, held high
    80: "MIC_LIVE",  # GPIO39
    81: "C6_RXD",  # GPIO40: P4 UART TX -> C6 RXD0 (flashing the C6 from the P4)
    82: "C6_TXD",  # GPIO41
    83: "C6_BOOT",  # GPIO42: C6 GPIO9 strap, open drain
    84: "STATE_LED",  # GPIO43
    86: "DDC_SDA_3V3", 87: "DDC_SCL_3V3",  # GPIO44/45
    88: "HDMI_CEC",  # GPIO46, open drain
    92: "LT_SDA", 93: "LT_SCL", 94: "I2S_BCLK", 95: "I2S_WS", 97: "I2S_DOUT", 98: "I2S_DIN",  # GPIO49-54
    105: "GND",
}  # fmt: skip

# LT8912B pin -> net.
LT_NETS = {
    # Data lanes P/N reversed on purpose (route_dsi): the LT8912B's data lanes are "polarity swappable"
    # (datasheet, features and pins 1-4); firmware sets the swap. The clock lane is not reversed.
    1: "DSI_D0_N", 2: "DSI_D0_P", 3: "DSI_D1_N", 4: "DSI_D1_P", 7: "DSI_CK_P", 8: "DSI_CK_N",
    5: "+1V8", 18: "+1V8", 26: "+1V8", 33: "+1V8", 34: "+1V8", 41: "+1V8", 50: "+1V8", 52: "+1V8", 57: "+1V8",
    6: "GND", 17: "GND", 23: "GND", 29: "GND", 32: "GND", 36: "GND", 42: "GND", 49: "GND", 51: "GND", 56: "GND",
    65: "GND",
    13: "LT_R6K", 14: "LT_HPD", 35: "LT_LPF", 53: "LT_XI", 54: "LT_XO",
    21: "HDMI_CK_N", 22: "HDMI_CK_P", 24: "HDMI_D0_N", 25: "HDMI_D0_P",
    27: "HDMI_D1_N", 28: "HDMI_D1_P", 30: "HDMI_D2_N", 31: "HDMI_D2_P",
    58: "I2S_DOUT", 59: "I2S_WS", 60: "I2S_BCLK", 61: "LT_SDA", 62: "LT_SCL", 64: "LT_RST_N",
}  # fmt: skip

HDMI_NETS = {
    1: "HDMI_D2_P", 3: "HDMI_D2_N", 4: "HDMI_D1_P", 6: "HDMI_D1_N",
    7: "HDMI_D0_P", 9: "HDMI_D0_N", 10: "HDMI_CK_P", 12: "HDMI_CK_N",
    2: "GND", 5: "GND", 8: "GND", 11: "GND", 17: "GND",
    13: "HDMI_CEC", 15: "DDC_SCL", 16: "DDC_SDA", 18: "+5VP", 19: "HDMI_HPD",
}  # fmt: skip

# C6 module pin -> net (ESP32-C6 datasheet IO MUX: SDIO CMD GPIO18, CLK 19, DATA0-3 GPIO20-23).
C6_NETS = {
    3: "+3V3", 8: "C6_EN", 22: "C6_IO8", 23: "C6_BOOT",
    24: "SDIO_CMD_C6", 25: "SDIO_CLK_C6", 26: "SDIO_D0_C6", 27: "SDIO_D1_C6", 28: "SDIO_D2_C6", 29: "SDIO_D3_C6",
    30: "C6_RXD", 31: "C6_TXD",
}  # fmt: skip
C6_GND = (1, 2, 11, 14, *range(36, 54))


def seg_len(points: list) -> float:
    return sum(math.dist(a, b) for a, b in itertools.pairwise(points))


def pad_at(d: kicadgen.Design, ref: str, number: str) -> tuple[float, float]:
    box = next(b for b in d.pad_boxes() if b.ref == ref and b.number == number)
    return (round((box.x1 + box.x2) / 2, 4), round((box.y1 + box.y2) / 2, 4))


def plug_ref(d: kicadgen.Design, pin: int) -> str:
    return "J3" if str(pin) in next(p for p in d.parts if p.ref == "J3").nets else "J3B"


def chamfered(corners: list, c: float) -> list:
    """A polyline through `corners` with each inner corner cut by a 45 degree chamfer of leg `c`."""
    out = [corners[0]]
    for a, b, n in zip(corners, corners[1:], corners[2:], strict=False):
        la, lb = math.dist(a, b), math.dist(b, n)
        ux, uy = (b[0] - a[0]) / la, (b[1] - a[1]) / la
        vx, vy = (n[0] - b[0]) / lb, (n[1] - b[1]) / lb
        out += [(b[0] - ux * min(c, la / 2), b[1] - uy * min(c, la / 2)), (b[0] + vx * min(c, lb / 2), b[1] + vy * min(c, lb / 2))]
    return [*out, corners[-1]]


def offset(points: list, o: float) -> list:
    """The polyline moved sideways by `o` (to the left of travel as the board shows it, y down),
    each corner the crossing of the two moved segments."""
    lines = []
    for a, b in itertools.pairwise(points):
        ln = math.dist(a, b)
        nx, ny = (b[1] - a[1]) / ln, -(b[0] - a[0]) / ln
        lines.append(((a[0] + o * nx, a[1] + o * ny), (b[0] + o * nx, b[1] + o * ny)))
    out = [lines[0][0]]
    for (p1, p2), (q1, q2) in itertools.pairwise(lines):
        d1, d2 = (p2[0] - p1[0], p2[1] - p1[1]), (q2[0] - q1[0], q2[1] - q1[1])
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-12:
            out.append(p2)
            continue
        t = ((q1[0] - p1[0]) * d2[1] - (q1[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + t * d1[0], p1[1] + t * d1[1]))
    return [*out, lines[-1][1]]


TMDS = [  # LT8912B P, N pin; plug +, - pin; name
    (31, 30, 1, 3, "D2"),
    (28, 27, 4, 6, "D1"),
    (25, 24, 7, 9, "D0"),
    (22, 21, 10, 12, "CK"),
]


def route_tmds(d: kicadgen.Design) -> list[str]:
    """The four TMDS pairs, LT8912B (U3) to the plug, drawn by hand.

    Each pair's centre line leaves U3's right side, jogs at 45 degrees to its pins' centre line,
    and the two traces run 0.2 mm either side of it (so a jog keeps their spacing). Ahead of the
    plug they split 0.3 mm each way to its 1.0 mm pin pitch, and run on F.Cu to the top contacts,
    or through a via pair onto B.Cu to the bottom ones. The pairs keep U3's order, so none cross."""
    report = []
    x_jog, x_split = LT_AT[0] + 5.0, PLUG_AT[0] - 6.2
    via_x = round(x_split + 0.9, 3)
    for lp, ln, hp, hn, name in TMDS:
        (xp0, yp0), (xn0, yn0) = pad_at(d, "U3", str(lp)), pad_at(d, "U3", str(ln))
        ref = plug_ref(d, hp)
        (xp1, yp1), (xn1, yn1) = pad_at(d, ref, str(hp)), pad_at(d, ref, str(hn))
        bottom = ref == "J3B"
        y0, y1 = (yp0 + yn0) / 2, (yp1 + yn1) / 2
        dy = y1 - y0
        xj = x_jog + (0.6 if name == "D0" else 0.0)  # D0 runs on 0.6 mm: room for U3 pin 26's via above it
        corners = [(xp0, y0), (xj, y0), (xj + abs(dy), y1), (x_split, y1)]
        centre = chamfered(corners, 0.4) if abs(dy) > 1e-6 else [(xp0, y0), (x_split, y1)]
        a, b = offset(centre, HALF), offset(centre, -HALF)
        p, n = (a, b) if abs(a[0][1] - yp0) < abs(b[0][1] - yp0) else (b, a)
        p[0], n[0] = (xp0, yp0), (xn0, yn0)
        end = via_x if bottom else xp1
        p += [(x_split + 0.3, yp1), (end, yp1)]
        n += [(x_split + 0.3, yn1), (end, yn1)]
        p = [(round(x, 4), round(y, 4)) for x, y in p]
        n = [(round(x, 4), round(y, 4)) for x, y in n]
        d.track(f"HDMI_{name}_P", p, "F.Cu", width=PAIR_W)
        d.track(f"HDMI_{name}_N", n, "F.Cu", width=PAIR_W)
        if bottom:
            for net, y, x1 in ((f"HDMI_{name}_P", yp1, xp1), (f"HDMI_{name}_N", yn1, xn1)):
                d.via(net, via_x, round(y, 4))
                d.track(net, [(via_x, round(y, 4)), (x1, round(y, 4))], "B.Cu", width=PAIR_W)
            p, n = [*p, (xp1, yp1)], [*n, (xn1, yn1)]
        report.append(
            f"{name}: P {seg_len(p):.3f} mm, N {seg_len(n):.3f} mm, skew {abs(seg_len(p) - seg_len(n)):.3f} mm"
        )
    return report


# DSI, drawn by hand (route_dsi). The pairs leave the P4's bottom row (D1, CK, D0 from the left) and
# run east under it in three lanes, then up into the LT8912B's bottom row (D0, D1, CK from the left).
# That U turns each pair over, so the data lanes land P/N reversed (LT_NETS); and CK, in the middle at
# the P4 but on the right at the LT8912B, has to cross D1: it drops to In2.Cu for the last 3.5 mm.
DSI_W, DSI_HALF = 0.14, 0.175  # 0.35 mm pitch, the P4's pin pitch: 0.21 mm gaps, about 98 ohm
LANE_D0, LANE_CK, LANE_D1 = BY + Y0 + 19.3, BY + Y0 + 20.05, BY + Y0 + 20.8  # under SW2 and the mic
JOG_D1, JOG_CK = BX + 56.7, BX + 58.0  # past SW2: D1 and CK step down to make room for CK's vias
DOWN_CK, DOWN_D1 = 0.35, 0.8
CK_VIAS_IN = ((BX + 61.9, LANE_CK + DOWN_CK - DSI_HALF), (BX + 62.5, BY + Y0 + 20.9))  # P, N: lane to In2.Cu
CK_VIAS_OUT = ((LT_AT[0] - 0.7, BY + Y0 + 18.4), (LT_AT[0], BY + Y0 + 18.95))  # P, N: In2.Cu to the pads
V1V8_VIA = (LT_AT[0] - 1.3, BY + Y0 + 19.4)  # U3 pin 5 (+1V8), boxed in between D1 and CK


def route_dsi(d: kicadgen.Design) -> list[str]:
    """The three DSI pairs, P4 (U1) to LT8912B (U3); see the note above. Returns a length report."""

    def pair(corners: list, a: tuple, b: tuple) -> tuple[list, list]:
        """Two traces either side of the chamfered centre line; the one starting nearer pad `a` first."""
        centre = chamfered(corners, 0.4)
        centre = [q for i, q in enumerate(centre) if i == 0 or math.dist(q, centre[i - 1]) > 1e-6]
        l, r = offset(centre, DSI_HALF), offset(centre, -DSI_HALF)
        return (l, r) if math.dist(l[0], a) < math.dist(r[0], a) else (r, l)

    def rnd(pts: list) -> list:
        return [(round(x, 4), round(y, 4)) for x, y in pts]

    def put(net: str, pts: list, layer: str = "F.Cu") -> None:
        d.track(net, rnd(pts), layer, width=DSI_W)

    report = []
    lengths = {}
    lanes = (("D0", "39", "40", "2", "1", LANE_D0), ("D1", "35", "36", "4", "3", LANE_D1))
    for name, up, un, lp, ln, lane in lanes:
        (xp, yp), (xn, yn) = pad_at(d, "U1", up), pad_at(d, "U1", un)
        (xlp, ylp), (xln, yln) = pad_at(d, "U3", lp), pad_at(d, "U3", ln)
        x0, xl = (xp + xn) / 2, (xlp + xln) / 2
        if name == "D0":
            corners = [(x0, yp), (x0, lane), (xl, lane), (xl, ylp)]
        else:
            low = lane + DOWN_D1
            corners = [(x0, yp), (x0, lane), (JOG_D1, lane), (JOG_D1 + DOWN_D1, low), (xl, low), (xl, ylp)]
        p, n = pair(corners, (xp, yp), (xn, yn))
        p[0], n[0] = (xp, yp), (xn, yn)
        # the U puts the P4's P trace on the LT8912B pin that LT_NETS names P (the swapped one)
        tp, tn = (xlp, ylp), (xln, yln)
        p[-1], n[-1] = (tp, tn) if math.dist(p[-1], tp) < math.dist(n[-1], tp) else (tn, tp)
        put(f"DSI_{name}_P", p)
        put(f"DSI_{name}_N", n)
        lengths[name] = (seg_len(p), seg_len(n))

    # CK: F.Cu lane, then In2.Cu under D1's riser, then up into pins 7 / 8.
    (xp, yp), (xn, yn) = pad_at(d, "U1", "38"), pad_at(d, "U1", "37")
    x0 = (xp + xn) / 2
    low = LANE_CK + DOWN_CK
    (vpx, vpy), (vnx, vny) = CK_VIAS_IN
    (opx, opy), (onx, ony) = CK_VIAS_OUT
    corners = [(x0, yp), (x0, LANE_CK), (JOG_CK, LANE_CK), (JOG_CK + DOWN_CK, low), (vpx - 0.4, low)]
    p, n = pair(corners, (xp, yp), (xn, yn))
    p[0], n[0] = (xp, yp), (xn, yn)
    p += [(vpx, vpy)]
    n += [(n[-1][0] + 0.3, vny), (vnx, vny)]
    put("DSI_CK_P", p)
    put("DSI_CK_N", n)
    pi = [(vpx, vpy), (opx - 0.3, vpy), (opx, vpy - 0.3), (opx, opy)]
    ni = [(vnx, vny), (onx - 0.3, vny), (onx, vny - 0.3), (onx, ony)]
    put("DSI_CK_P", pi, "In2.Cu")
    put("DSI_CK_N", ni, "In2.Cu")
    (x7, y7), (x8, y8) = pad_at(d, "U3", "7"), pad_at(d, "U3", "8")
    pe = [(opx, opy), (x7, opy - 0.5), (x7, y7)]
    ne = [(onx, ony), (x8, ony - 0.35), (x8, y8)]
    put("DSI_CK_P", pe)
    put("DSI_CK_N", ne)
    for net, at in (("DSI_CK_P", (vpx, vpy)), ("DSI_CK_N", (vnx, vny)), ("DSI_CK_P", (opx, opy)), ("DSI_CK_N", (onx, ony))):
        d.via(net, round(at[0], 4), round(at[1], 4))
    lengths["CK"] = (seg_len(p) + seg_len(pi) + seg_len(pe), seg_len(n) + seg_len(ni) + seg_len(ne))

    # U3 pin 5 (+1V8) between D1 and CK: down to a via of its own. Pin 6 (GND) into the exposed pad.
    (x5, y5), (x6, y6) = pad_at(d, "U3", "5"), pad_at(d, "U3", "6")
    vx, vy = V1V8_VIA
    d.track("+1V8", rnd([(x5, y5), (x5, vy - 0.6), (vx, vy - 0.5), (vx, vy)]), "F.Cu", width=0.2)
    d.via("+1V8", vx, vy)
    d.track("GND", rnd([(x6, y6), (x6, y6 - 1.0)]), "F.Cu", width=0.2)

    for name, (lp, ln) in lengths.items():
        report.append(f"{name}: P {lp:.3f} mm, N {ln:.3f} mm, skew {abs(lp - ln):.3f} mm")
    return report


def tie_pad_grounds(d: kicadgen.Design, refs: dict[str, tuple[int, int]]) -> None:
    """Each GND pad of the fine-pitch parts joins ground: a QFN's straight into its exposed pad on a
    short inward track (the vias there take it down), otherwise a via and a short track off the
    pad's end. The inward tie keeps the ring outside the pads free for signals to escape."""
    r, drill = d.via_size / 2, d.via_drill
    for part in d.parts:
        if part.ref not in refs:
            continue
        gnd = [b for b in d.pad_boxes() if b.ref == part.ref and b.net == "GND" and b.kind == "smd"]
        ep = next((b for b in gnd if (b.x2 - b.x1) > 2 and (b.y2 - b.y1) > 2), None)
        for pad in gnd:
            if pad is ep:
                continue  # vias inside it instead
            cx, cy = round((pad.x1 + pad.x2) / 2, 3), round((pad.y1 + pad.y2) / 2, 3)
            if ep is not None:
                tall = (pad.y2 - pad.y1) > (pad.x2 - pad.x1)
                ix = cx if tall else (ep.x1 + 0.1 if cx < ep.x1 else ep.x2 - 0.1)
                iy = (ep.y1 + 0.1 if cy < ep.y1 else ep.y2 - 0.1) if tall else cy
                if _stub_fits(d, "GND", (cx, cy), (ix, iy), 0.15, part.pcb_layer, d.pad_boxes()):
                    d.track("GND", [(cx, cy), (round(ix, 3), round(iy, 3))], part.pcb_layer, width=0.15)
                    continue
            first = refs[part.ref]
            if first == (0, 0):  # off the pad's outer end, away from the part's centre
                ox, oy = part.pcb_at
                tall = (pad.y2 - pad.y1) > (pad.x2 - pad.x1)
                first = (0, 1 if cy > oy else -1) if tall else (1 if cx > ox else -1, 0)
            boxes = d.pad_boxes()
            for sx, sy in (first, (-first[0], -first[1])):
                vx = cx if sx == 0 else round((pad.x2 if sx > 0 else pad.x1) + sx * (0.12 + r), 3)
                vy = cy if sy == 0 else round((pad.y2 if sy > 0 else pad.y1) + sy * (0.12 + r), 3)
                # r + HOLE_MARGIN: the hole keeps 0.25 mm to other copper (the board's hole clearance)
                if d._via_fits(vx, vy, r + HOLE_MARGIN, drill, "GND", boxes):
                    d.track("GND", [(cx, cy), (vx, vy)], part.pcb_layer, width=0.2)
                    d.via("GND", vx, vy)
                    break


# A via placed beside a pad grows by this much in the fit check: a little room on top of the
# 0.25 mm hole clearance that the 0.15 mm copper clearance already gives a 0.4 / 0.2 mm via.
HOLE_MARGIN = 0.02


def stitch_grounds(d: kicadgen.Design, gaps: tuple[float, ...] = (0.1, 0.25, 0.45)) -> int:
    """kicadgen's stitch_pads, with the hole clearance kept: a GND via beside each GND pad on a pour.

    Tries each side at the nearest gap first; a via further out than the first gap gets a short
    track to its pad, so a pad boxed in by its neighbours (the decoupling under the LT8912B) still
    reaches the plane. Returns the number of vias placed."""
    r, drill = d.via_size / 2, d.via_drill
    boxes = d.pad_boxes()
    placed = 0
    for pad in boxes:
        if pad.net != "GND" or pad.kind != "smd" or pad.layer not in ("F.Cu", "B.Cu"):
            continue
        cx, cy = (pad.x1 + pad.x2) / 2, (pad.y1 + pad.y2) / 2
        for gap in gaps:
            spots = ((cx, pad.y2 + gap + r), (cx, pad.y1 - gap - r), (pad.x2 + gap + r, cy), (pad.x1 - gap - r, cy))
            spot = next((v for v in spots if d._via_fits(v[0], v[1], r + HOLE_MARGIN, drill, "GND", boxes)), None)
            if spot:
                vx, vy = round(spot[0], 3), round(spot[1], 3)
                if gap > gaps[0]:
                    d.track("GND", [(round(cx, 3), round(cy, 3)), (vx, vy)], pad.layer, width=0.2)
                d.via("GND", vx, vy)
                placed += 1
                break
    return placed


def _seg_point_dist(a: tuple, b: tuple, q: tuple) -> float:
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((q[0] - ax) * dx + (q[1] - ay) * dy) / ll))
    return math.dist((ax + t * dx, ay + t * dy), q)


def _seg_box_dist(a: tuple, b: tuple, box: tuple) -> float:
    """Distance from segment ab to an axis-aligned box (0 when they touch), by sampling the segment."""
    x1, y1, x2, y2 = box
    n = max(2, int(math.dist(a, b) / 0.02) + 1)
    best = 1e9
    for i in range(n):
        t = i / (n - 1)
        px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        dx, dy = max(x1 - px, 0.0, px - x2), max(y1 - py, 0.0, py - y2)
        best = min(best, math.hypot(dx, dy))
    return best


def _stub_fits(d: kicadgen.Design, net: str, a: tuple, b: tuple, w: float, layer: str, boxes: list) -> bool:
    """A track of `net` from a to b on `layer` keeps the clearance from other nets' pads, tracks, vias."""
    need = d.clearance + 0.01 + w / 2
    lo_x, hi_x, lo_y, hi_y = min(a[0], b[0]) - 1, max(a[0], b[0]) + 1, min(a[1], b[1]) - 1, max(a[1], b[1]) + 1
    for bx in boxes:
        if bx.net == net or bx.x2 < lo_x or bx.x1 > hi_x or bx.y2 < lo_y or bx.y1 > hi_y:
            continue
        if (bx.layer == layer or bx.kind != "smd") and _seg_box_dist(a, b, (bx.x1, bx.y1, bx.x2, bx.y2)) < need:
            return False
    for onet, p0, p1, ow, olayer in d.segments:
        if onet == net or olayer != layer:
            continue
        if max(p0[0], p1[0]) < lo_x or min(p0[0], p1[0]) > hi_x or max(p0[1], p1[1]) < lo_y or min(p0[1], p1[1]) > hi_y:
            continue
        n = max(2, int(math.dist(a, b) / 0.02) + 1)
        for i in range(n):
            q = (a[0] + (b[0] - a[0]) * i / (n - 1), a[1] + (b[1] - a[1]) * i / (n - 1))
            if _seg_point_dist(p0, p1, q) < need + ow / 2:
                return False
    for onet, (vx, vy), size, _drill in d.vias:
        if onet != net and _seg_point_dist(a, b, (vx, vy)) < need + size / 2:
            return False
    return True


def _pad_frame(pad, ox: float, oy: float) -> tuple:
    """Centre, outer end, outward unit vector and lateral offset from the part's centre line of a QFN pad."""
    cx, cy = (pad.x1 + pad.x2) / 2, (pad.y1 + pad.y2) / 2
    if (pad.y2 - pad.y1) > (pad.x2 - pad.x1):
        ux, uy = 0.0, (1.0 if cy > oy else -1.0)
        end = (cx, pad.y2 if uy > 0 else pad.y1)
    else:
        ux, uy = (1.0 if cx > ox else -1.0), 0.0
        end = (pad.x2 if ux > 0 else pad.x1, cy)
    off = (cx - ox) * uy + (cy - oy) * ux  # along the lateral axis the via search uses
    return (cx, cy), end, (ux, uy), off


def _try_spot(d: kicadgen.Design, pad, centre, spot, boxes) -> tuple | None:
    """Stub and via for `pad` at `spot` when both keep every clearance; returns what it added."""
    vx, vy = round(spot[0], 3), round(spot[1], 3)
    if not d._via_fits(vx, vy, d.via_size / 2 + HOLE_MARGIN, d.via_drill, pad.net, boxes):
        return None
    if not _stub_fits(d, pad.net, centre, (vx, vy), 0.12, pad.layer, boxes):
        return None
    net = pad.net.removeprefix("/")  # pad boxes carry the board's net name
    d.track(net, [(round(centre[0], 3), round(centre[1], 3)), (vx, vy)], pad.layer, width=0.12)
    d.via(net, vx, vy)
    return d.segments[-1], d.vias[-1]


FAN_T, FAN_SPREAD, ESCAPE = (0.5, 1.3), 0.3, 0.8
SEARCH_T = (0.45, 0.55, 0.65, 0.75, 1.05, 1.35, 1.65, 1.95, 2.3, 2.7, 3.1, 3.5)
SEARCH_LAT = (0.0, 0.2, -0.2, 0.4, -0.4, 0.6, -0.6, 0.9, -0.9, 1.2, -1.2, 1.5, -1.5)


FAN_MAZE = True
FAN_PITCH, FAN_REACH = 0.6, 0.6  # the fan's via pitch, and how far past the pad end its middle via stands


def _runs(pads: list, ox: float, oy: float) -> list[list]:
    """Runs of neighbouring pads on one side, in order along the side, the longest run first."""
    side = {b.number: _pad_frame(b, ox, oy)[2] for b in pads}
    runs: list[list] = []
    for b in sorted(pads, key=lambda b: int(b.number)):
        if runs and int(b.number) - int(runs[-1][-1].number) == 1 and side[b.number] == side[runs[-1][-1].number]:
            runs[-1].append(b)
        else:
            runs.append([b])
    for run in runs:
        run.sort(key=lambda b: _pad_frame(b, ox, oy)[3])  # along the lateral axis
    return sorted(runs, key=len, reverse=True)


def _fan_path(d: kicadgen.Design, pad, ox: float, oy: float, boxes: list, reach: float, shift: float) -> tuple | None:
    """Straight out of the pad, then 45 degrees sideways by `shift` to a via `reach` mm past the pad's
    end: a run's tracks keep the 0.35 mm pitch while straight and splay into one row of vias
    FAN_PITCH apart, so no track passes between two vias."""
    centre, end, (ux, uy), _ = _pad_frame(pad, ox, oy)
    lx, ly = uy, ux  # the lateral axis _pad_frame's offset is measured on
    bend = reach - abs(shift)
    pts = [centre, (end[0] + ux * bend, end[1] + uy * bend), (end[0] + ux * reach + lx * shift, end[1] + uy * reach + ly * shift)]
    pts = [(round(x, 3), round(y, 3)) for x, y in pts]
    if abs(shift) < 0.001:
        pts = [pts[0], pts[2]]
    vx, vy = pts[-1]
    if not d._via_fits(vx, vy, d.via_size / 2 + HOLE_MARGIN, d.via_drill, pad.net, boxes):
        return None
    if not all(_stub_fits(d, pad.net, a, b, 0.12, pad.layer, boxes) for a, b in itertools.pairwise(pts)):
        return None
    name = pad.net.removeprefix("/")
    d.track(name, pts, pad.layer, width=0.12)
    d.via(name, vx, vy)
    return d.segments[-(len(pts) - 1):], d.vias[-1]


def fanout(d: kicadgen.Design, ref: str, skip: set[str]) -> tuple[int, list[str]]:
    """A via for each signal and supply pad of a fine-pitch part, on a short stub off the pad's outer
    end, before routing: FreeRouting then only joins vias, which it does far better than threading
    0.35 mm pitch pads. A straight stub can never pass a neighbour's via at that pitch, so the vias
    fan out: two rows (even pads near, odd pads further), each via pushed sideways away from the
    middle of its side by FAN_SPREAD of its offset. A pad whose fan spot is taken (a part, a hand
    route) searches rows further out and to either side. Returns (vias placed, pads left without one)."""
    part = next(p for p in d.parts if p.ref == ref)
    ox, oy = part.pcb_at
    pads = [b for b in d.pad_boxes() if b.ref == ref and b.kind == "smd" and b.net and b.net != "GND"]
    pads = [b for b in pads if b.net.removeprefix("/") not in skip and not b.net.startswith("unconnected")]
    pads = [b for b in pads if (b.x2 - b.x1) < 2 and (b.y2 - b.y1) < 2]  # not the exposed pad
    got = {b.number: None for b in pads}
    boxes = d.pad_boxes()

    def lane_free(pad) -> bool:
        """A pad without a via keeps a straight lane out for the router, ESCAPE mm past its end."""
        centre, end, (ux, uy), _ = _pad_frame(pad, ox, oy)
        return _stub_fits(d, pad.net, centre, (end[0] + ux * ESCAPE, end[1] + uy * ESCAPE), 0.12, pad.layer, boxes)

    open_lane = {b.number for b in pads if lane_free(b)}  # lanes other parts already close are not ours to keep

    def place(pad, spot) -> tuple | None:
        """_try_spot, kept only if every pad still without a via keeps its lane."""
        added = _try_spot(d, pad, _pad_frame(pad, ox, oy)[0], spot, boxes)
        if added and not all(lane_free(b) for b in pads if got[b.number] is None and b is not pad and b.number in open_lane):
            d.segments.remove(added[0])
            d.vias.remove(added[1])
            return None
        return added

    if FAN_MAZE:
        for run in _runs(pads, ox, oy):
            mid = (len(run) - 1) / 2
            reach = FAN_REACH + mid * (FAN_PITCH - 0.35)
            for i in sorted(range(len(run)), key=lambda i: abs(i - mid)):
                got[run[i].number] = _fan_path(d, run[i], ox, oy, boxes, reach, (i - mid) * (FAN_PITCH - 0.35))
        for run in _runs(pads, ox, oy):  # what the fan could not place: a path search, near rows first
            for pad in run:
                if got[pad.number] is None:
                    got[pad.number] = _maze_escape(d, pad, ox, oy, boxes)
    for pad in sorted(pads, key=lambda b: int(b.number) % 2):  # the near row first: far stubs pass between it
        if got[pad.number] is not None:
            continue
        _, end, (ux, uy), off = _pad_frame(pad, ox, oy)
        t, lat = FAN_T[int(pad.number) % 2], FAN_SPREAD * off
        got[pad.number] = place(pad, (end[0] + ux * t + uy * lat, end[1] + uy * t + ux * lat))
    for pad in pads:
        if got[pad.number] is not None:
            continue
        _, end, (ux, uy), off = _pad_frame(pad, ox, oy)
        sign = 1.0 if off >= 0 else -1.0
        for t in SEARCH_T:
            for lat in (None, *SEARCH_LAT):  # None: straight out, where pairs on both sides splay apart
                lat = 0.0 if lat is None else FAN_SPREAD * off + sign * lat
                spot = (end[0] + ux * t + uy * lat, end[1] + uy * t + ux * lat)
                got[pad.number] = place(pad, spot)
                if got[pad.number]:
                    break
            if got[pad.number]:
                break
    for pad in sorted(pads, key=lambda b: abs(_pad_frame(b, ox, oy)[3]), reverse=True):  # corners first
        if got[pad.number] is None:
            got[pad.number] = _maze_escape(d, pad, ox, oy, boxes)
    left = sorted((n for n, g in got.items() if g is None), key=int)
    nets = {b.number: b.net + ("" if lane_free(b) else " (boxed in)" if b.number in open_lane else " (no lane)") for b in pads}
    return sum(g is not None for g in got.values()), [f"{ref}.{n} {nets[n]}" for n in left]


MAZE_STEP, MAZE_REACH = 0.025, 3.0


def _maze_escape(d: kicadgen.Design, pad, ox: float, oy: float, boxes: list, reach: float = 0.0) -> tuple | None:
    """A bent stub on the pad's layer to the nearest free via spot, for a pad no straight stub serves:
    its neighbours' vias stand 1-1.6 mm out, so a straight line always meets one. Dijkstra on a
    MAZE_STEP grid anchored on the pad's centre, 45 degree moves, turns cost extra; the grid only
    proposes, _stub_fits and _via_fits decide. Returns the tracks and via it added."""
    centre, end, (ux, uy), _ = _pad_frame(pad, ox, oy)
    net, layer, w = pad.net, pad.layer, 0.12
    step, n = MAZE_STEP, int(MAZE_REACH / MAZE_STEP)
    need = d.clearance + 0.01 + w / 2 + 0.018  # the grid's own error, step / sqrt(2)
    vneed = d.clearance + d.via_size / 2 + HOLE_MARGIN + 0.018
    lo_x, hi_x, lo_y, hi_y = centre[0] - MAZE_REACH, centre[0] + MAZE_REACH, centre[1] - MAZE_REACH, centre[1] + MAZE_REACH
    track_block, via_block = set(), set()

    def mark(x1, y1, x2, y2, grow, into):
        """Cells closer than `grow` to the box (x1, y1, x2, y2)."""
        i1, i2 = math.floor((x1 - grow - centre[0]) / step), math.ceil((x2 + grow - centre[0]) / step)
        j1, j2 = math.floor((y1 - grow - centre[1]) / step), math.ceil((y2 + grow - centre[1]) / step)
        for i in range(max(i1, -n), min(i2, n) + 1):
            px = centre[0] + i * step
            for j in range(max(j1, -n), min(j2, n) + 1):
                py = centre[1] + j * step
                if math.hypot(max(x1 - px, 0.0, px - x2), max(y1 - py, 0.0, py - y2)) < grow:
                    into.add((i, j))

    for bx in boxes:
        if bx.x2 < lo_x - 1 or bx.x1 > hi_x + 1 or bx.y2 < lo_y - 1 or bx.y1 > hi_y + 1:
            continue
        if bx.net != net:
            mark(bx.x1, bx.y1, bx.x2, bx.y2, vneed, via_block)
            if bx.layer == layer or bx.kind != "smd":
                mark(bx.x1, bx.y1, bx.x2, bx.y2, need, track_block)
    for onet, p0, p1, ow, olayer in d.segments:
        if onet.removeprefix("/") == net.removeprefix("/"):
            continue
        if max(p0[0], p1[0]) < lo_x - 1 or min(p0[0], p1[0]) > hi_x + 1:
            continue
        if max(p0[1], p1[1]) < lo_y - 1 or min(p0[1], p1[1]) > hi_y + 1:
            continue
        k = max(2, int(math.dist(p0, p1) / (step / 2)) + 1)
        for t in range(k):
            q = (p0[0] + (p1[0] - p0[0]) * t / (k - 1), p0[1] + (p1[1] - p0[1]) * t / (k - 1))
            mark(q[0], q[1], q[0], q[1], vneed + ow / 2, via_block)
            if olayer == layer:
                mark(q[0], q[1], q[0], q[1], need + ow / 2, track_block)
    for onet, (vx, vy), size, _drill in d.vias:
        if onet.removeprefix("/") != net.removeprefix("/") and lo_x - 1 < vx < hi_x + 1 and lo_y - 1 < vy < hi_y + 1:
            mark(vx, vy, vx, vy, need + size / 2, track_block)
            mark(vx, vy, vx, vy, vneed + size / 2 + 0.05, via_block)

    def at(c):
        return (round(centre[0] + c[0] * step, 3), round(centre[1] + c[1] * step, 3))

    def out_of_pad(c):
        q = at(c)
        return (q[0] - end[0]) * ux + (q[1] - end[1]) * uy > max(reach, d.via_size / 2 + 0.15)

    moves = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
    start = (0, 0)
    best = {(start, None): 0.0}
    parent = {}
    heap = [(0.0, start, None)]
    tried = 0
    while heap and tried < 60:
        cost, c, md = heapq.heappop(heap)
        if cost > best.get((c, md), 1e9):
            continue
        if c not in via_block and c != start and out_of_pad(c):
            path, key = [c], (c, md)
            while key in parent:
                key = parent[key]
                path.append(key[0])
            path.reverse()
            pts = [path[0]]
            for a, b, e in zip(path, path[1:], path[2:], strict=False):
                if (b[0] - a[0], b[1] - a[1]) != (e[0] - b[0], e[1] - b[1]):
                    pts.append(b)
            pts.append(path[-1])
            pts = [at(q) for q in pts]
            pts[0] = (round(centre[0], 3), round(centre[1], 3))
            tried += 1
            vx, vy = pts[-1]
            if d._via_fits(vx, vy, d.via_size / 2 + HOLE_MARGIN, d.via_drill, net, boxes) and all(
                _stub_fits(d, net, a, b, w, layer, boxes) for a, b in itertools.pairwise(pts)
            ):
                name = net.removeprefix("/")
                d.track(name, pts, layer, width=w)
                d.via(name, vx, vy)
                k = len(pts) - 1
                return d.segments[-k:], d.vias[-1]
            continue
        for mv in moves:
            q = (c[0] + mv[0], c[1] + mv[1])
            if abs(q[0]) > n or abs(q[1]) > n or q in track_block:
                continue
            if c == start and (mv[0] * ux + mv[1] * uy) <= 0:
                continue  # leave the pad outward
            nc = cost + math.hypot(*mv) + (0.0 if md in (None, mv) else 1.5)
            if nc < best.get((q, mv), 1e9):
                best[(q, mv)] = nc
                parent[(q, mv)] = (c, md)
                heapq.heappush(heap, (nc, q, mv))
    return None


def preroute(d: kicadgen.Design) -> None:
    """The connections FreeRouting leaves open, routed first by finish.py --pre on the unrouted
    board (prerouted.json), added as fixed copper: the router routes the rest around them.
    AGENTCAST_PREROUTE=0 leaves them out, for finish.py to route them again."""
    path = Path(__file__).with_name("prerouted.json")
    if os.environ.get("AGENTCAST_PREROUTE") == "0" or not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    gone = {
        (c["net"], c["layer"], (round(c["a"][0], 4), round(c["a"][1], 4)), (round(c["b"][0], 4), round(c["b"][1], 4)))
        for c in data.get("removed", [])
    }
    if gone:  # fanout stubs a prerouted connection runs through
        def kept_seg(seg) -> bool:
            net, a, b, _w, layer = seg
            return (net.removeprefix("/"), layer, (round(a[0], 4), round(a[1], 4)), (round(b[0], 4), round(b[1], 4))) not in gone

        def kept_via(via) -> bool:
            net, at, _size, _drill = via
            xy = (round(at[0], 4), round(at[1], 4))
            return (net.removeprefix("/"), None, xy, xy) not in gone

        d.segments[:] = [s for s in d.segments if kept_seg(s)]
        d.vias[:] = [v for v in d.vias if kept_via(v)]
    for c in data["copper"]:
        if c["layer"] is None:
            d.via(c["net"], c["a"][0], c["a"][1])
        else:
            d.track(c["net"], [tuple(c["a"]), tuple(c["b"])], c["layer"], width=0.12)


def ep_vias(d: kicadgen.Design, ref: str, number: str, side: float, n: int) -> list[tuple[float, float]]:
    """An n x n grid of GND vias inside an exposed pad of side `side`; returns where they are."""
    cx, cy = pad_at(d, ref, number)
    step = side / n
    spots = []
    for i in range(n):
        for j in range(n):
            x, y = round(cx - side / 2 + step * (i + 0.5), 3), round(cy - side / 2 + step * (j + 0.5), 3)
            d.via("GND", x, y)
            spots.append((x, y))
    return spots


def placed_box(part: kicadgen.Part) -> tuple[float, float, float, float]:
    """A part's courtyard on the board, as kicadgen places it (B.Cu mirrors y, then the turn)."""
    x1, y1, x2, y2 = part.footprint.courtyard
    back = part.pcb_layer == "B.Cu"
    th = math.radians(part.pcb_rot)
    px, py = part.pcb_at
    xs, ys = [], []
    for fx, fy in ((x1, y1), (x1, y2), (x2, y1), (x2, y2)):
        fy = -fy if back else fy
        xs.append(px + fx * math.cos(th) + fy * math.sin(th))
        ys.append(py - fx * math.sin(th) + fy * math.cos(th))
    return (min(xs), min(ys), max(xs), max(ys))


def legalize(d: kicadgen.Design, fixed: set[str], keep: dict[str, list[tuple]], obstacles: dict[str, tuple]) -> list[str]:
    """Move each part not in `fixed` to the free spot nearest to where it was put.

    Free means: its courtyard clear of every part already placed on its face, of every hole (any
    face), of the `keep` areas of its face, inside the board 0.3 mm from the edge and clear of the
    antenna strip. `obstacles` overrides a fixed part's box (the C6 module's courtyard includes its
    antenna keep-out beyond the board). Returns the parts moved, with how far."""
    def overlap(a, b, m=0.0):
        return a[0] < b[2] + m and b[0] < a[2] + m and a[1] < b[3] + m and b[1] < a[3] + m

    boxes = {"F.Cu": [], "B.Cu": []}
    holes = []
    for part in d.parts:
        if not part.footprint or not part.pcb_at:
            continue
        for pb in d.pad_boxes():
            if pb.ref == part.ref and pb.kind in ("thru_hole", "np_thru_hole") and pb.layer in ("F.Cu", ""):
                holes.append((pb.x1, pb.y1, pb.x2, pb.y2))
        if part.ref in fixed:
            boxes[part.pcb_layer].append(obstacles.get(part.ref) or placed_box(part))
    for pb in d.pad_boxes():  # through pads appear once per layer; any one marks the hole
        if pb.kind in ("thru_hole", "np_thru_hole"):
            holes.append((pb.x1, pb.y1, pb.x2, pb.y2))
    movable = [p for p in d.parts if p.footprint and p.pcb_at and p.ref not in fixed]

    def area(p: kicadgen.Part) -> float:
        b = placed_box(p)
        return (b[2] - b[0]) * (b[3] - b[1])

    movable.sort(key=lambda p: -area(p))
    steps = sorted(
        ((i * 0.25, j * 0.25) for i in range(-24, 25) for j in range(-24, 25)), key=lambda v: math.hypot(*v)
    )
    moved = []
    for part in movable:
        x0, y0 = part.pcb_at
        for dx, dy in steps:
            part.pcb_at = (round(x0 + dx, 3), round(y0 + dy, 3))
            b = placed_box(part)
            if b[0] < BX + 6.8 or b[1] < BY + 0.3 or b[2] > BX + W - 0.3 or b[3] > BY + H - 0.3:
                continue
            if any(overlap(b, o, 0.05) for o in boxes[part.pcb_layer]):
                continue
            if any(overlap(b, h, 0.25) for h in holes):
                continue
            if any(overlap(b, k) for k in keep.get(part.pcb_layer, [])):
                continue
            break
        else:
            raise ValueError(f"{part.ref}: no free spot within 6 mm of {x0, y0}")
        boxes[part.pcb_layer].append(placed_box(part))
        if (dx, dy) != (0, 0):
            moved.append(f"{part.ref} {math.hypot(dx, dy):.2f} mm")
    return moved


def auto_schematic(d: kicadgen.Design, order: list[list[str]], width: float = 800.0) -> None:
    """Lay the sheet out in blocks: each inner list is one block, its parts in a row, wrapping."""
    x, y, row_h, gap = 30.48, 30.48, 0.0, 15.24
    for block in order:
        for ref in block:
            part = next(p for p in d.parts if p.ref == ref)
            bx0, by0, bx1, by1 = kicadgen.symbol_box(part.symbol)  # the body; pins reach past it
            bx0, by0, bx1, by1 = bx0 - 5.08, by0 - 5.08, bx1 + 5.08, by1 + 5.08
            w, h = bx1 - bx0, by1 - by0
            if x + w > width:
                x, y, row_h = 30.48, y + row_h + gap, 0.0
            part.sch_at = (round((x - bx0) / 2.54) * 2.54, round((y - by0) / 2.54) * 2.54)
            x += w + gap
            row_h = max(row_h, h)
        x, y, row_h = 30.48, y + row_h + gap, 0.0


def build() -> kicadgen.Design:
    d = StickDesign(name="agentcast_dongle", namespace=uuid.UUID("0b9e2d4a-7c31-4f86-b5a2-9d3e61f08c57"))
    d.copper_layers = 8
    d.plane_layers = ("In1.Cu", "In6.Cu")
    d.sheet = "A1"
    d.sch_wires = True
    d.outline = (BX, BY, BX + W, BY + H)
    d.corner_radius = (2.5, 0.0, 0.0, 2.5)  # round at the far end, square at the plug end
    d.symbol_dirs = {"Agentcast": LIB / "agentcast.kicad_sym"}
    d.footprint_dirs = {"Agentcast": LIB / "agentcast.pretty"}
    d.track_width = 0.12
    # 0.15, not 0.12: a 0.4 / 0.2 mm via's ring (0.1) plus 0.15 keeps its hole 0.25 mm from other
    # copper, the board's hole clearance, which the router does not model by itself.
    d.clearance = 0.15
    d.edge_clearance = 0.3
    d.via_size = 0.4
    d.via_drill = 0.2
    # JLCPCB multilayer limits (README fab notes): 0.09 mm trace and gap, 0.15 mm hole, 0.25 mm via.
    d.rules = {"min_through_hole_diameter": 0.2, "min_via_diameter": 0.4, "min_text_height": 0.8}
    d.net_classes = {
        "HDMI": {"width": PAIR_W, "clearance": 0.15, "via": 0.4, "via_drill": 0.2,
                 "nets": [f"HDMI_{t[4]}_{s}" for t in TMDS for s in "PN"]},
        "Power": {"width": 0.2, "clearance": 0.15, "via": 0.4, "via_drill": 0.2,
                  "nets": ["GND", "+5V", "+3V3", "VDD_HP", "+1V8"]},
    }  # fmt: skip
    d.power_nets = {"GND": "GND", "+5V": "+5V", "+3V3": "+3V3", "+1V8": "+1V8", "+5VP": "+5VP", "VDD_HP": "+1V1",
                    "MIC_3V3": "VDD", "VDDO_FLASH": "VCC"}
    # +1V8, +5VP, MIC_1V8 and VBUS_HOST are driven by their regulators' outputs; these are not.
    d.flagged_nets = ["GND", "+5V", "+3V3", "VDD_HP", "MIC_3V3", "VDDO_FLASH"]
    d.check_pulls = True
    d.defined_nets = {
        "C6_IO8": "10k pull-up R31 to +3V3 (C6 strap: GPIO8 high)",
        "EN_DCDC": "driven by the ESP32-P4's own power control (HDG 1.3.2); 0 V until firmware runs",
        "FLASH_CK": "driven by the ESP32-P4's dedicated FLASH_CK output (datasheet pin 32)",
        "MIC_BCLK": "driven by U13's output through the 33 ohm series resistor",
        "MIC_WS": "driven by U14's output through the 33 ohm series resistor",
        "MUTED": "held low through the MUTED LED's resistor and the LED while SW2 is in LIVE",
        "I2S_BCLK": "driven by the ESP32-P4's I2S (GPIO51); U13 has Ioff while MIC_1V8 is off",
        "I2S_WS": "driven by the ESP32-P4's I2S (GPIO52); U14 has Ioff while MIC_1V8 is off",
    }

    def add(ref, sym, value, fp, at, nets, rot=0, layer="F.Cu"):
        return d.add(ref, sym, value, fp, sch_at=(0, 0), pcb_at=(BX + at[0], BY + Y0 + at[1]), pcb_rot=rot,
                     pcb_layer=layer, nets=nets)  # fmt: skip

    R0402, C0402, C0603 = "Resistor_SMD:R_0402_1005Metric", "Capacitor_SMD:C_0402_1005Metric", "Capacitor_SMD:C_0603_1608Metric"
    C0805, LED0603 = "Capacitor_SMD:C_0805_2012Metric", "LED_SMD:LED_0603_1608Metric"
    SOT235, SOT236, SOT23 = "Package_TO_SOT_SMD:SOT-23-5", "Package_TO_SOT_SMD:SOT-23-6", "Package_TO_SOT_SMD:SOT-23"
    XTAL = "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm"
    L2520 = "Inductor_SMD:L_1008_2520Metric"
    USBC = "Connector_USB:USB_C_Receptacle_GCT_USB4085"
    n_r = itertools.count(1)
    n_c = itertools.count(1)

    def R(value, at, a, b, rot=0, layer="B.Cu"):
        ref = f"R{next(n_r)}"
        add(ref, "Device:R_Small", value, R0402, at, {"1": a, "2": b}, rot, layer)
        return ref

    def C(value, at, a, b="GND", rot=0, layer="B.Cu", fp=None):
        ref = f"C{next(n_c)}"
        fp = fp or (C0805 if value in ("22u",) else C0603 if value in ("10u", "4.7u") else C0402)
        add(ref, "Device:C_Small", value, fp, at, {"1": a, "2": b}, rot, layer)
        return ref

    # ---------------------------------------------------------------- the computer
    p4 = table("esp32p4_pins.csv")
    add("U1", "Agentcast:ESP32-P4", "ESP32-P4NRW32", "Agentcast:QFN-104-1EP_10x10mm_P0.35mm_EP7.5x7.5mm",
        (P4_AT[0] - BX, P4_AT[1] - BY - Y0), {str(k): v for k, v in P4_NETS.items() if k in p4})  # fmt: skip
    # Decoupling on the bottom face under U1's sides (HDG 1.3.2: 0.1 uF at each supply pin).
    cx, cy = P4_AT[0] - BX, P4_AT[1] - BY - Y0
    for net, dx, dy, rot in (
        ("+3V3", -4.2, -2.0, 90), ("+3V3", -4.2, 2.0, 90), ("+3V3", 4.2, 2.6, 90), ("+3V3", 1.5, -4.2, 0),
        ("VDD_HP", -4.2, 3.8, 90), ("VDD_HP", 4.2, 0.6, 90), ("VDD_HP", 4.2, -1.6, 90), ("VDD_HP", -1.0, -4.2, 0),
        ("+1V8", 0.5, -4.2, 0), ("VDDO_FLASH", -2.4, 4.2, 0), ("VDDO_PSRAM", 3.0, 4.2, 0), ("VDD_MIPI", -0.5, 4.2, 0),
    ):  # fmt: skip
        C("100n", (cx + dx, cy + dy), net, rot=rot)
    C("10u", (cx + 7.4, cy - 3.0), "+3V3", rot=90)
    C("22u", (cx + 7.4, cy + 1.0), "VDD_HP", rot=90)
    C("1u", (cx + 7.4, cy + 4.0), "VDDO_FLASH", rot=90)
    C("1u", (cx + 1.5, cy + 6.3), "VDDO_PSRAM")
    C("1u", (cx - 1.5, cy + 6.3), "VDD_MIPI")
    C("1u", (cx + 4.0, cy - 7.2), "VDDO_4")
    R("4.02k", (cx - 3.6, cy + 6.3), "DSI_REXT", "GND")  # DSI PHY reference (datasheet pin 34)
    # Core supply: TLV62569 per HDG Fig. 5 (chip revision v3.0 and later).
    add("U5", "Regulator_Switching:TLV62569DBV", "TLV62569DBV", SOT235, (cx + 8.0, 3.2),
        {"4": "+3V3", "1": "EN_DCDC", "3": "SW_HP", "2": "GND", "5": "FB_DCDC"}, rot=90)  # fmt: skip
    add("L1", "Device:L", "2.2u", L2520, (cx + 8.0, 7.2), {"1": "SW_HP", "2": "VDD_HP"}, rot=90)
    C("4.7u", (cx + 10.2, 3.2), "+3V3", rot=90, layer="F.Cu")
    R("499k", (cx + 10.4, 7.2), "VDD_HP", "FB_DCDC", rot=90, layer="F.Cu")
    R("499k", (cx + 11.6, 7.2), "FB_DCDC", "GND", rot=90, layer="F.Cu")
    C("22p", (cx + 12.8, 7.2), "VDD_HP", "FB_DCDC", rot=90, layer="F.Cu")
    # 40 MHz crystal (HDG 1.4.2: the firmware supports 40 MHz only, +/-10 ppm).
    add("Y1", "Device:Crystal_GND24", "40MHz 10ppm", XTAL, (cx - 2.6, 3.2), {"1": "XTAL_P", "3": "XTAL_N", "2": "GND", "4": "GND"})
    C("12p", (cx - 5.0, 3.2), "XTAL_P", rot=90, layer="F.Cu")
    C("12p", (cx - 0.2, 3.2), "XTAL_N", rot=90, layer="F.Cu")
    # Reset RC on CHIP_PU (HDG 1.3.3: 10k / 1 uF), reset and boot buttons on the bottom face.
    R("10k", (cx - 6.2, cy - 5.5), "+3V3", "CHIP_PU", rot=90)
    C("1u", (cx - 7.4, cy - 5.5), "CHIP_PU", rot=90)
    add("SW1", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_B3U-1000P", (cx - 9.5, 3.0), {"1": "BOOT", "2": "GND"}, layer="B.Cu")
    add("SW3", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_B3U-1000P", (cx - 9.5, 7.0), {"1": "CHIP_PU", "2": "GND"}, layer="B.Cu")
    R("10k", (cx - 6.2, cy - 8.0), "+3V3", "BOOT", rot=90)
    R("10k", (cx - 7.4, cy - 8.0), "+3V3", "GPIO36_PU", rot=90)
    # Flash, 16 MB quad SPI, left of the DSI lanes (all its pins on the P4's side), on VDDO_FLASH (3.3 V default, HDG Table 1); CS pulled up (HDG 1.3.4).
    add("U4", "Memory_Flash:W25Q128JVP", "W25Q128JVPIQ", "Package_SON:WSON-8-1EP_6x5mm_P1.27mm_EP3.4x4.3mm",
        (cx - 5.6, cy + 9.0), {"1": "FLASH_CS", "2": "FLASH_Q", "3": "FLASH_WP", "4": "GND", "5": "FLASH_D",
                               "6": "FLASH_CK", "7": "FLASH_HOLD", "8": "VDDO_FLASH", "9": "GND"}, layer="B.Cu")  # fmt: skip
    R("10k", (cx - 9.4, cy + 7.2), "VDDO_FLASH", "FLASH_CS", rot=90)
    C("100n", (cx - 1.4, cy + 9.0), "VDDO_FLASH", rot=90)

    # ---------------------------------------------------------------- HDMI bridge and plug
    lt = table("lt8912b_pins.csv")
    ux, uy = LT_AT[0] - BX, LT_AT[1] - BY - Y0
    add("U3", "Agentcast:LT8912B", "LT8912B", "Agentcast:QFN-64-1EP_7.5x7.5mm_P0.4mm_EP6.2x6.2mm", (ux, uy),
        {str(k): v for k, v in LT_NETS.items() if k in lt}, rot=90)  # fmt: skip
    for dx, dy, rot in ((-3.6, -1.0, 90), (-3.6, 1.0, 90), (3.6, -2.0, 90), (3.6, 0.8, 90), (0.0, -3.6, 0), (-1.8, 3.6, 0), (1.8, 3.6, 0)):
        C("100n", (ux + dx, uy + dy), "+1V8", rot=rot)
    C("10u", (ux - 2.0, uy - 6.0), "+1V8", layer="F.Cu")
    R("6.04k", (ux + 3.0, uy + 6.2), "LT_R6K", "GND", layer="F.Cu")  # LT8912B pin 13: external 6K
    C("2.2n", (ux + 2.4, uy - 6.0), "LT_LPF", layer="F.Cu")  # pin 35: 2 nF loop filter
    # LT8912B crystal: the datasheet asks for one on XTALI/XTALO but gives no frequency (README).
    add("Y2", "Device:Crystal_GND24", "25MHz (confirm)", XTAL, (ux - 7.4, uy), {"1": "LT_XI", "3": "LT_XO", "2": "GND", "4": "GND"}, rot=90)
    C("12p", (ux - 6.8, uy - 3.0), "LT_XI", layer="F.Cu")
    C("12p", (ux - 6.8, uy + 3.0), "LT_XO", layer="F.Cu")
    # +1V8: LT8912B and P4 IO bank 6.
    add("U6", "Regulator_Linear:TLV75518PDBV", "TLV75518PDBV", SOT235, (ux + 2.5, 3.0),
        {"1": "+3V3", "3": "+3V3", "2": "GND", "5": "+1V8"}, rot=90)  # fmt: skip
    C("1u", (ux + 4.5, 3.0), "+3V3", rot=90, layer="F.Cu")
    C("1u", (ux + 0.5, 3.0), "+1V8", rot=90, layer="F.Cu")
    R("10k", (ux + 5.0, uy - 6.0), "+1V8", "LT_RST_N", layer="F.Cu")
    R("4.7k", (ux + 5.0, uy + 6.0), "+1V8", "LT_SDA", layer="F.Cu")
    R("4.7k", (ux + 6.2, uy + 6.0), "+1V8", "LT_SCL", rot=90, layer="F.Cu")

    for ref, sym, fp, layer, pins in (
        ("J3", "HDMI_A_Plug_Top", "HDMI_A_Plug_XUNPU_HDMI-003_Top", "F.Cu", range(2, 19, 2)),
        ("J3B", "HDMI_A_Plug_Bottom", "HDMI_A_Plug_XUNPU_HDMI-003_Bottom", "B.Cu", range(1, 20, 2)),
    ):
        nets = {str(k): HDMI_NETS[k] for k in pins if k in HDMI_NETS}
        nets["SH"] = "GND"
        d.add(ref, f"Agentcast:{sym}", "HDMI-003" if ref == "J3" else "HDMI-003 (bottom contacts)", f"Agentcast:{fp}",
              sch_at=(0, 0), pcb_at=PLUG_AT, pcb_rot=90 if layer == "F.Cu" else 270, pcb_layer=layer, nets=nets)  # fmt: skip
    # HDMI +5V (pin 18): TPS2051C, current limit and reverse blocking; EN from +3V3.
    add("U7", "Power_Management:TPS2051CDBV", "TPS2051CDBV", SOT235, (72.0, 22.0),
        {"5": "+5V", "4": "+3V3", "1": "+5VP", "2": "GND"}, layer="B.Cu")  # fmt: skip
    C("100n", (72.0, 24.6), "+5VP")
    # HPD (5 V from the TV) into the LT8912B's 1.8 V-referenced input: 18k / 10k (+100k inside).
    R("18k", (72.5, 19.0), "HDMI_HPD", "LT_HPD", rot=90)
    R("10k", (73.7, 19.0), "LT_HPD", "GND", rot=90)
    # DDC (EDID) at 5 V to the P4's 3.3 V I2C through BSS138 shifters; source pull-ups 1.8k to +5VP.
    for k, (line, gpio) in enumerate((("DDC_SDA", "DDC_SDA_3V3"), ("DDC_SCL", "DDC_SCL_3V3"))):
        add(f"Q{k + 1}", "Transistor_FET:BSS138", "BSS138", SOT23, (71.5 - 3.0 * k, 4.5),
            {"1": "+3V3", "2": gpio, "3": line}, rot=90, layer="B.Cu")  # fmt: skip
        R("1.8k", (71.5 - 3.0 * k, 7.6), "+5VP", line, rot=90)
        R("4.7k", (71.5 - 3.0 * k, 1.8), "+3V3", gpio, rot=90)
    # CEC: 3.3 V open drain straight to the plug (HDMI CEC is 3.3 V); 27k pull-up.
    R("27k", (66.5, 1.8), "+3V3", "HDMI_CEC", rot=90)

    # ---------------------------------------------------------------- Wi-Fi
    add("U2", "RF_Module:ESP32-C6-MINI-1", "ESP32-C6-MINI-1", "RF_Module:ESP32-C6-MINI-1",
        (C6_AT[0] - BX, C6_AT[1] - BY - Y0), {**{str(k): v for k, v in C6_NETS.items()}, **{str(k): "GND" for k in C6_GND}},
        rot=90)  # fmt: skip
    C("10u", (13.5, 2.2), "+3V3", rot=90)
    C("100n", (15.0, 2.2), "+3V3", rot=90)
    R("10k", (16.5, 2.2), "+3V3", "C6_EN", rot=90)
    C("1u", (18.0, 2.2), "C6_EN", rot=90)
    R("10k", (13.5, 23.8), "+3V3", "C6_IO8", rot=90)
    R("10k", (15.0, 23.8), "+3V3", "C6_BOOT", rot=90)
    # SDIO: 22 ohm series and 10k pull-up on each line (HDG 1.3.11).
    for k, sig in enumerate(("CLK", "CMD", "D0", "D1", "D2", "D3")):
        R("22", (18.5, 7.0 + 1.6 * k), f"SDIO_{sig}", f"SDIO_{sig}_C6")
        R("10k", (20.5, 7.0 + 1.6 * k), "+3V3", f"SDIO_{sig}")

    # ---------------------------------------------------------------- power in, USB
    add("J4", "Connector:USB_C_Receptacle_USB2.0_16P", "USB4085-GF-A", USBC, (USB_PWR_AT[0] - BX, USB_PWR_AT[1] - BY - Y0),
        {"A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
         "A4": "+5V", "A9": "+5V", "B4": "+5V", "B9": "+5V", "A5": "CC1", "B5": "CC2",
         "A6": "J4_DP", "B6": "J4_DP", "A7": "J4_DN", "B7": "J4_DN"}, rot=180)  # fmt: skip
    R("5.1k", (21.0, 10.5), "CC1", "GND", rot=90)  # a sink: Rd 5.1k on each CC (USB Type-C spec)
    R("5.1k", (22.2, 10.5), "CC2", "GND", rot=90)
    add("U8", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", SOT236, (26.5, 11.0),
        {"1": "J4_DP", "6": "J4_DP", "3": "J4_DN", "4": "J4_DN", "2": "GND", "5": "+5V"}, rot=90, layer="B.Cu")  # fmt: skip
    R("22", (28.8, 10.2), "J4_DP", "USB_FS_DP")  # HDG 1.3.12: 22/33 ohm near the chip
    R("22", (28.8, 11.8), "J4_DN", "USB_FS_DN")
    # +3V3: TLV62569 from +5V, 0.6 V x (1 + 100k / 22.1k) = 3.31 V (TLV62569 datasheet, Vfb 0.6 V).
    add("U9", "Regulator_Switching:TLV62569DBV", "TLV62569DBV", SOT235, (21.0, 13.0),
        {"4": "+5V", "1": "+5V", "3": "SW_3V3", "2": "GND", "5": "FB_3V3"}, rot=90)  # fmt: skip
    add("L2", "Device:L", "2.2u", L2520, (24.0, 13.0), {"1": "SW_3V3", "2": "+3V3"}, rot=90)
    C("10u", (21.0, 16.0), "+5V", layer="F.Cu")
    C("22u", (27.0, 13.0), "+3V3", rot=90, layer="F.Cu")
    R("100k", (23.0, 16.0), "+3V3", "FB_3V3", layer="F.Cu")
    R("22.1k", (25.0, 16.0), "FB_3V3", "GND", layer="F.Cu")
    C("22u", (17.5, 13.0), "+5V", rot=90, layer="F.Cu")
    add("J6", "Connector:USB_C_Receptacle_USB2.0_16P", "USB4085-GF-A", USBC, (USB_HOST_AT[0] - BX, USB_HOST_AT[1] - BY - Y0),
        {"A1": "GND", "B1": "GND", "A12": "GND", "B12": "GND", "SH": "GND",
         "A4": "VBUS_HOST", "A9": "VBUS_HOST", "B4": "VBUS_HOST", "B9": "VBUS_HOST", "A5": "CC1_H", "B5": "CC2_H",
         "A6": "USB_HS_DP", "B6": "USB_HS_DP", "A7": "USB_HS_DN", "B7": "USB_HS_DN"})  # fmt: skip
    add("U10", "Power_Protection:TPD2EUSB30", "TPD2EUSB30", "Package_TO_SOT_SMD:Texas_DRT-3", (26.5, 16.0),
        {"1": "USB_HS_DP", "2": "USB_HS_DN", "3": "GND"}, layer="B.Cu")  # fmt: skip
    # External mic power: TPS2051C enabled by MIC_3V3, so the mute switch cuts it.
    add("U11", "Power_Management:TPS2051CDBV", "TPS2051CDBV", SOT235, (21.0, 18.5),
        {"5": "+5V", "4": "MIC_3V3", "1": "VBUS_HOST", "2": "GND"}, rot=90, layer="B.Cu")  # fmt: skip
    C("10u", (17.8, 18.5), "VBUS_HOST", rot=90)
    R("56k", (23.5, 18.5), "VBUS_HOST", "CC1_H", rot=90)  # Rp 56k: default USB power (USB Type-C spec)
    R("56k", (24.7, 18.5), "VBUS_HOST", "CC2_H", rot=90)

    # ---------------------------------------------------------------- mic and mute
    add("SW2", "Switch:SW_SPDT", "PCM12SMTR", "Button_Switch_SMD:SW_SPDT_PCM12", (MUTE_AT[0] - BX, MUTE_AT[1] - BY - Y0),
        {"2": "+3V3", "1": "MIC_3V3", "3": "MUTED"})  # fmt: skip
    R("100k", (49.0, 21.0), "MIC_3V3", "GND", rot=90)  # bleed; holds U11's enable low when muted
    R("1k", (57.8, 21.4), "MIC_3V3", "LED_LIVE_A", layer="B.Cu")
    add("D1", "Device:LED", "green LIVE", LED0603, (57.8, 23.0), {"2": "LED_LIVE_A", "1": "GND"}, rot=180)
    R("1k", (57.8, 24.6), "MUTED", "LED_MUTED_A", layer="B.Cu")
    add("D2", "Device:LED", "red MUTED", LED0603, (60.2, 23.6), {"2": "LED_MUTED_A", "1": "GND"}, rot=90)
    R("10k", (50.2, 21.0), "MIC_3V3", "MIC_LIVE", rot=90)
    R("100k", (51.4, 21.0), "MIC_LIVE", "GND", rot=90)
    add("U12", "Regulator_Linear:AP2112K-1.8", "AP2112K-1.8", SOT235, (33.0, 20.2),
        {"1": "MIC_3V3", "3": "MIC_3V3", "2": "GND", "5": "MIC_1V8"}, layer="B.Cu")  # fmt: skip
    C("1u", (30.4, 20.2), "MIC_3V3", rot=90)
    C("1u", (35.8, 21.4), "MIC_1V8", rot=90)
    add("MK1", "Agentcast:ICS-43434_TS", "ICS-43434", "Sensor_Audio:InvenSense_ICS-43434-6_3.5x2.65mm",
        (MIC_AT[0] - BX, MIC_AT[1] - BY - Y0), {"1": "MIC_WS", "2": "GND", "3": "GND", "4": "MIC_BCLK", "5": "MIC_1V8", "6": "I2S_DIN"})  # fmt: skip
    C("100n", (35.6, 23.5), "MIC_1V8", rot=90, layer="F.Cu")
    sc70 = "Package_TO_SOT_SMD:SOT-353_SC-70-5"
    add("U13", "74xGxx:74LVC1G34", "74LVC1G34", sc70, (32.0, 11.0), {"2": "I2S_BCLK", "4": "BCLK_B", "3": "GND", "5": "MIC_1V8"}, layer="B.Cu")
    add("U14", "74xGxx:74LVC1G34", "74LVC1G34", sc70, (35.0, 11.0), {"2": "I2S_WS", "4": "WS_B", "3": "GND", "5": "MIC_1V8"}, layer="B.Cu")
    R("33", (32.0, 13.4), "BCLK_B", "MIC_BCLK", rot=90)
    R("33", (35.0, 13.4), "WS_B", "MIC_WS", rot=90)
    C("100n", (33.5, 13.4), "MIC_1V8", rot=90)
    R("100k", (30.4, 11.0), "I2S_DIN", "GND", rot=90)  # tri-stated SD line (ICS-43434 datasheet)

    # ---------------------------------------------------------------- LEDs
    R("2.2k", (30.5, 2.0), "+5V", "LED_PWR_A", layer="F.Cu")
    add("D3", "Device:LED", "green PWR", LED0603, (30.5, 3.6), {"2": "LED_PWR_A", "1": "GND"}, rot=180)
    R("330", (60.0, 21.0), "STATE_LED", "LED_STATE_A", layer="B.Cu")
    add("D4", "Device:LED", "amber STATE", LED0603, (62.4, 23.6), {"2": "LED_STATE_A", "1": "GND"}, rot=90)

    for part in d.parts:  # references on the fab layer only for the small parts (README)
        if part.ref[0] in "RCDLQY" or part.ref.startswith(("SW", "U5", "U6", "U7", "U8", "U9", "U1", "J4", "J6")):
            part.hide_ref = True

    auto_schematic(d, [
        ["J4", "U8", "U9", "L2", "U12", "U11", "U10", "J6"],
        ["U1", "U5", "L1", "Y1", "U4", "SW1", "SW3"],
        ["U3", "Y2", "U6", "J3", "J3B", "U7", "Q1", "Q2"],
        ["U2", "SW2", "MK1", "U13", "U14", "D1", "D2", "D3", "D4"],
        sorted((p.ref for p in d.parts if p.ref[0] in "RC"), key=lambda r: (r[0], int(r[1:]))),
    ])

    # Small parts: the nearest free spot to where each was put. Kept clear: the HDMI and DSI lanes
    # (F.Cu), the exposed pads' ground vias (B.Cu), the mic's sound hole. The C6 module's box is its
    # body's courtyard (module y -5.6..5.85, x +/-6.85, turned); its antenna strip is off limits anyway.
    vias = ep_vias(d, "U1", "105", 7.5, 4) + ep_vias(d, "U3", "65", 6.2, 3)
    via_boxes = [(x - 0.4, y - 0.4, x + 0.4, y + 0.4) for x, y in [*vias, *CK_VIAS_IN, *CK_VIAS_OUT, V1V8_VIA]]
    mx, my = MIC_AT
    d.moved = legalize(
        d,
        fixed={"U1", "U2", "U3", "J3", "J3B", "J4", "J6", "SW2", "MK1"},
        keep={
            "F.Cu": [(LT_AT[0] + 3.8, BY + Y0 + 8.4, PLUG_AT[0] - 2.6, BY + Y0 + 17.6),
                     (P4_AT[0] - 1.8, BY + Y0 + 18.25, LT_AT[0] + 0.6, BY + Y0 + 21.0),  # DSI lanes
                     (JOG_D1 - 0.4, BY + Y0 + 21.0, LT_AT[0] - 1.8, BY + Y0 + 21.95),
                     (mx - 0.6, my + 0.1, mx + 0.6, my + 1.3)],
            "B.Cu": [*via_boxes, (mx - 0.6, my + 0.1, mx + 0.6, my + 1.3)],
        },
        obstacles={"U2": (C6_AT[0] - 5.6, C6_AT[1] - 6.85, C6_AT[0] + 5.85, C6_AT[1] + 6.85)},
    )  # fmt: skip

    # Copper: In1.Cu and In6.Cu solid GND planes (the references of F.Cu and B.Cu); In2.Cu to In5.Cu
    # routing layers (on 4 and 6 layers the router left 20-30 connections around the P4); both faces GND.
    poly = [(BX + 6.8, BY + 0.3), (BX + W - 0.3, BY + 0.3), (BX + W - 0.3, BY + H - 0.3), (BX + 6.8, BY + H - 0.3)]
    d.zone("GND", layers=("In1.Cu", "In6.Cu"), polygon=poly, connect="solid")
    d.zone("GND", layers=("F.Cu", "B.Cu"), polygon=poly, clearance=0.25, connect="solid")
    d.keepout(ANTENNA, layers=("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "In6.Cu", "B.Cu"), name="antenna")

    d.tmds_report = route_tmds(d)
    d.dsi_report = route_dsi(d)
    tie_pad_grounds(d, {"U1": (0, 0), "U3": (0, 0), "J3": (-1, 0), "J3B": (-1, 0)})
    dsi = {f"DSI_{n}_{s}" for n in ("D0", "D1", "CK") for s in "PN"}
    hdmi = {f"HDMI_{n}_{s}" for n in ("D0", "D1", "D2", "CK") for s in "PN"}
    d.fanout = {ref: fanout(d, ref, dsi | hdmi) for ref in ("U1", "U3")}
    preroute(d)
    stitch_grounds(d)
    d.model("J3", "${KIPRJMOD}/models/hdmi_a_plug.wrl", offset=(0.0, -5.65, -2.9))

    d.text("AGENTCAST v0.5", BX + 54.0, BY + 1.6, "B.SilkS", 1.0, 0.15)
    d.text("MUTE", MUTE_AT[0], BY + H - 6.4, "F.SilkS", 0.8, 0.12)
    return d
