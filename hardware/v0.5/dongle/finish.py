"""Finish the routed board: route every connection FreeRouting left open, then refill the pours.

FreeRouting leaves the same 20-odd connections open around the P4 however the board is laid out:
the last fraction of a millimetre into a pad its neighbours' vias and tracks box in. This takes the
DRC's unconnected items (build/drc.json) and routes each open net with a shortest-path search on a
GRID mm grid over the routing layers (F.Cu, In2.Cu to In5.Cu, B.Cu), changing layer through a via
where one fits. It rips up and reroutes: the search may cross another net's routed track or via at
a price, the crossed copper is removed, and that net goes back in the queue; a net's price grows
each time it is ripped, so the nets settle (negotiated congestion). Pads, the board edge, keepouts,
GND copper and the hand-drawn pairs (PROTECTED) are never crossed. A GND pad or pour cut off from
the rest takes a via down to the In1.Cu / In6.Cu planes, and pour islands with no pad are removed.

Rules come from the board (clearance, edge clearance, via size and drill) plus HOLE_MARGIN for the
0.25 mm hole clearance (design.py's note). The DRC decides: run `workcenter drc .` afterwards.

    python3 finish.py [board_dir]
"""

from __future__ import annotations

import heapq
import itertools
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pcbnew

GRID = 0.025
WIDTH = 0.12  # the board's track width (design.py track_width)
HOLE_MARGIN = 0.02  # as design.py: the router does not model the 0.25 mm hole clearance
SLACK = 0.03  # a cell centre stands up to GRID / sqrt(2) from the copper it stands for
VIA_COST = 40  # in cells: a via weighs a millimetre of track
RIP_COST, RIP_GROWTH = 20.0, 2.0  # per cell of another net's copper crossed, times (1 + growth * rips)
GREED = 1.5  # weighted A*: faster, a little longer than shortest
MAX_ROUTES = 400
ROUTING = ("F.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "In5.Cu", "B.Cu")
PROTECTED = ("GND", "/DSI_", "/HDMI_")  # nets whose copper is never ripped (prefixes)
FREE, BLOCKED = 0, -1


def mm(v: int) -> float:
    return pcbnew.ToMM(v)


FIXED: set[str] = set()  # nets prerouted in this run: never ripped either


def protected(name: str) -> bool:
    return name in FIXED or any(name == p or name.startswith(p) for p in PROTECTED)


class Grid:
    """Per routing layer, which net's grown copper covers each cell (FREE, a net code, or BLOCKED
    where two nets' do), plus one layer for vias, which pass every layer. `hard` holds what is never
    moved; `soft` holds routed tracks and vias that may be ripped."""

    def __init__(self, board: pcbnew.BOARD) -> None:
        self.board = board
        ds = board.GetDesignSettings()
        self.clear = max(mm(ds.m_MinClearance), mm(ds.m_NetSettings.GetDefaultNetclass().GetClearance()))
        self.edge = mm(ds.m_CopperEdgeClearance)
        self.via_d, self.via_drill = mm(ds.GetCurrentViaSize()), mm(ds.GetCurrentViaDrill())
        box = board.GetBoardEdgesBoundingBox()
        self.x0, self.y0 = mm(box.GetX()), mm(box.GetY())
        self.nx, self.ny = int(mm(box.GetWidth()) / GRID) + 2, int(mm(box.GetHeight()) / GRID) + 2
        self.layers = {name: board.GetLayerID(name) for name in ROUTING}
        self.xs = self.x0 + np.arange(self.nx) * GRID
        self.ys = self.y0 + np.arange(self.ny) * GRID
        self.tgrow = self.clear + WIDTH / 2 + SLACK  # a track centre this far from other copper
        self.vgrow = self.clear + self.via_d / 2 + HOLE_MARGIN + SLACK
        self.inside = _inside_outline(board, self.xs, self.ys)
        self.pads = []  # read once: the footprint list does not survive tracks being removed
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                bb, p = pad.GetBoundingBox(), pad.GetPosition()
                self.pads.append({
                    "net": pad.GetNetCode(),
                    "shape": ("box", (mm(bb.GetLeft()), mm(bb.GetTop())), (mm(bb.GetRight()), mm(bb.GetBottom())), 0),
                    "layers": [n for n in ROUTING if pad.IsOnLayer(self.layers[n])],
                    "hole": mm(pad.GetDrillSizeX()) if pad.HasHole() else 0.0,
                    "npth": pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH,
                    "at": (mm(p.x), mm(p.y)),
                })
        # the copper as plain data: [net, name, layer or None for a via, a, b, half width, drill]
        self.copper = []
        for t in board.GetTracks():
            if t.Type() == pcbnew.PCB_VIA_T:
                p = t.GetPosition()
                c = (mm(p.x), mm(p.y))
                self.copper.append([t.GetNetCode(), t.GetNetname(), None, c, c, mm(t.GetWidth(pcbnew.F_Cu)) / 2,
                                    mm(t.GetDrill())])
            else:
                s0, e = t.GetStart(), t.GetEnd()
                self.copper.append([t.GetNetCode(), t.GetNetname(), t.GetLayerName(), (mm(s0.x), mm(s0.y)),
                                    (mm(e.x), mm(e.y)), mm(t.GetWidth()) / 2, 0.0])
        self.rebuild()

    def rebuild(self) -> None:
        z = np.zeros((self.nx, self.ny), np.int32)
        self.hard = {name: z.copy() for name in ROUTING}
        self.soft = {name: z.copy() for name in ROUTING}
        self.hard_via, self.soft_via = z.copy(), z.copy()
        self._fill()

    def cell(self, x: float, y: float) -> tuple[int, int]:
        return round((x - self.x0) / GRID), round((y - self.y0) / GRID)

    def at(self, i: int, j: int) -> tuple[float, float]:
        return round(self.x0 + i * GRID, 4), round(self.y0 + j * GRID, 4)

    def mark(self, arr: np.ndarray, net: int, shape, grow: float) -> None:
        """Cells within `grow` of `shape` take `net` (BLOCKED where another net is already)."""
        kind, a, b, r = shape  # ("box", (x1, y1), (x2, y2), 0) or ("seg", p0, p1, half width)
        x1, y1 = min(a[0], b[0]) - r - grow, min(a[1], b[1]) - r - grow
        x2, y2 = max(a[0], b[0]) + r + grow, max(a[1], b[1]) + r + grow
        i1, j1 = max(0, math.floor((x1 - self.x0) / GRID)), max(0, math.floor((y1 - self.y0) / GRID))
        i2, j2 = min(self.nx - 1, math.ceil((x2 - self.x0) / GRID)), min(self.ny - 1, math.ceil((y2 - self.y0) / GRID))
        if i1 > i2 or j1 > j2:
            return
        px, py = np.meshgrid(self.xs[i1 : i2 + 1], self.ys[j1 : j2 + 1], indexing="ij")
        if kind == "box":
            dx = np.maximum(np.maximum(a[0] - px, 0), px - b[0])
            dy = np.maximum(np.maximum(a[1] - py, 0), py - b[1])
            dist = np.hypot(dx, dy)
        else:
            vx, vy = b[0] - a[0], b[1] - a[1]
            ll = vx * vx + vy * vy
            t = np.zeros_like(px) if ll == 0 else np.clip(((px - a[0]) * vx + (py - a[1]) * vy) / ll, 0, 1)
            dist = np.hypot(px - (a[0] + t * vx), py - (a[1] + t * vy)) - r
        hit = dist < grow
        sub = arr[i1 : i2 + 1, j1 : j2 + 1]
        sub[hit & (sub != net) & (sub != FREE)] = BLOCKED
        sub[hit & (sub == FREE)] = net

    def add_copper(self, net: int, shape, layers, hole: float = 0.0, soft: bool = False) -> None:
        """A piece of copper on `layers`; a hole keeps vias' holes 0.25 mm away whatever the nets."""
        track, via = (self.soft, self.soft_via) if soft else (self.hard, self.hard_via)
        for name in layers:
            if name in track:
                self.mark(track[name], net, shape, self.tgrow)
        self.mark(via, net, shape, self.vgrow)
        if hole > 0:
            _, a, b, _ = shape
            centre = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            self.mark(via, BLOCKED, ("seg", centre, centre, hole / 2), 0.25 + self.via_drill / 2 + SLACK)

    def _fill(self) -> None:
        b = self.board
        names = list(ROUTING)
        for pad in self.pads:
            shape = pad["shape"]
            if pad["npth"]:  # board edge to the DRC
                for n in names:
                    self.mark(self.hard[n], BLOCKED, shape, self.edge + WIDTH / 2 + SLACK)
                self.mark(self.hard_via, BLOCKED, shape, self.edge + self.via_d / 2 + SLACK)
                continue
            self.add_copper(pad["net"] if pad["net"] > 0 else BLOCKED, shape, pad["layers"], pad["hole"])
        for net, name, layer, a, e, r, drill in self.copper:
            soft = not protected(name)
            if layer is None:
                self.add_copper(net, ("seg", a, a, r), names, drill, soft)
            elif layer in names:
                shape = ("seg", a, e, r)
                self.mark((self.soft if soft else self.hard)[layer], net, shape, self.tgrow)
                self.mark(self.soft_via if soft else self.hard_via, net, shape, self.vgrow)
        for z in b.Zones():
            if not z.GetIsRuleArea():
                continue
            bb = z.GetBoundingBox()
            shape = ("box", (mm(bb.GetLeft()), mm(bb.GetTop())), (mm(bb.GetRight()), mm(bb.GetBottom())), 0)
            for n in names:
                if z.IsOnLayer(self.layers[n]):
                    self.mark(self.hard[n], BLOCKED, shape, WIDTH / 2 + SLACK)
            self.mark(self.hard_via, BLOCKED, shape, self.via_d / 2 + SLACK)
        for d in b.GetDrawings():
            if d.GetLayer() != pcbnew.Edge_Cuts:
                continue
            for seg in _edge_segments(d):
                for n in names:
                    self.mark(self.hard[n], BLOCKED, ("seg", *seg, 0), self.edge + WIDTH / 2 + SLACK)
                self.mark(self.hard_via, BLOCKED, ("seg", *seg, 0), self.edge + self.via_d / 2 + SLACK)
        for n in names:
            self.hard[n][~self.inside] = BLOCKED
        self.hard_via[~self.inside] = BLOCKED


def _edge_segments(d) -> list[tuple]:
    """Board-edge shapes as straight pieces."""
    if d.GetShape() == pcbnew.SHAPE_T_SEGMENT:
        s, e = d.GetStart(), d.GetEnd()
        return [((mm(s.x), mm(s.y)), (mm(e.x), mm(e.y)))]
    poly = pcbnew.SHAPE_POLY_SET()
    d.TransformShapeToPolygon(poly, pcbnew.Edge_Cuts, 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
    out = []
    for k in range(poly.OutlineCount()):
        ol = poly.Outline(k)
        pts = [ol.CPoint(i) for i in range(ol.PointCount())]
        for p, q in zip(pts, pts[1:] + pts[:1], strict=False):
            out.append(((mm(p.x), mm(p.y)), (mm(q.x), mm(q.y))))
    return out


def _inside_outline(b: pcbnew.BOARD, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Cells inside the board outline (even-odd rule over the outline's edges)."""
    outline = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(outline, False)
    px, py = np.meshgrid(xs, ys, indexing="ij")
    out = np.zeros(px.shape, bool)
    for k in range(outline.OutlineCount()):
        for ring in [outline.Outline(k)] + [outline.Hole(k, h) for h in range(outline.HoleCount(k))]:
            pts = [(mm(ring.CPoint(i).x), mm(ring.CPoint(i).y)) for i in range(ring.PointCount())]
            for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1], strict=False):
                if y1 == y2:
                    continue
                crosses = (y1 > py) != (y2 > py)
                xcross = x1 + (py - y1) * (x2 - x1) / (y2 - y1)
                out ^= crosses & (px < xcross)
    return out


def own_cells(g: Grid, net: int) -> dict:
    """The net's own copper, cell by cell and layer by layer, as clusters joined across layers by
    vias and through pads: {(layer, i, j): cluster id}."""
    cells: dict = {}
    links = []  # cells where copper passes every layer

    def add(layer: str, shape) -> None:
        kind, a, c, r = shape
        x1, y1 = min(a[0], c[0]) - r, min(a[1], c[1]) - r
        x2, y2 = max(a[0], c[0]) + r, max(a[1], c[1]) + r
        for i in range(math.floor((x1 - g.x0) / GRID), math.ceil((x2 - g.x0) / GRID) + 1):
            for j in range(math.floor((y1 - g.y0) / GRID), math.ceil((y2 - g.y0) / GRID) + 1):
                px, py = g.at(i, j)
                if kind == "box":
                    inside = x1 <= px <= x2 and y1 <= py <= y2
                else:
                    inside = _seg_dist(a, c, (px, py)) <= r
                if inside:
                    cells[(layer, i, j)] = None

    for pad in g.pads:
        if pad["net"] != net:
            continue
        for n in pad["layers"]:
            add(n, pad["shape"])
        if len(pad["layers"]) > 2:
            links.append(g.cell(*pad["at"]))
    for onet, _name, layer, a, e, r, _drill in g.copper:
        if onet != net:
            continue
        if layer is None:
            for n in ROUTING:
                add(n, ("seg", a, a, r))
            links.append(g.cell(*a))
        elif layer in ROUTING:
            add(layer, ("seg", a, e, r))
    link_set = set(links)
    cid = 0
    for start in list(cells):
        if cells[start] is not None:
            continue
        stack = [start]
        cells[start] = cid
        while stack:
            layer, i, j = stack.pop()
            nbrs = [(layer, i + di, j + dj) for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1))]
            if (i, j) in link_set:
                nbrs += [(n, i, j) for n in ROUTING]
            for q in nbrs:
                if q in cells and cells[q] is None:
                    cells[q] = cid
                    stack.append(q)
        cid += 1
    return cells


def _seg_dist(a, b, q) -> float:
    vx, vy = b[0] - a[0], b[1] - a[1]
    ll = vx * vx + vy * vy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((q[0] - a[0]) * vx + (q[1] - a[1]) * vy) / ll))
    return math.hypot(q[0] - a[0] - t * vx, q[1] - a[1] - t * vy)


def search(g: Grid, net: int, src: set, dst, price: dict, reach: float = 4.0):
    """Cheapest path from any cell of `src` to any of `dst` ({(layer, i, j)}, or "via": any spot a
    via fits, for GND), through cells the net's or free of fixed copper; crossing another net's
    routed copper costs that net's price. Returns the cell path."""
    to_via = dst == "via"
    pts = list(src) if to_via else list(src) + list(dst)
    span = int(reach / GRID)
    lo_i, hi_i = min(c[1] for c in pts) - span, max(c[1] for c in pts) + span
    lo_j, hi_j = min(c[2] for c in pts) - span, max(c[2] for c in pts) + span
    goal = [] if to_via else [(c[1], c[2]) for c in list(dst)[:: max(1, len(dst) // 24)]]

    def h(i, j):
        return GREED * min((math.hypot(i - a, j - b) for a, b in goal), default=0.0)

    def step_cost(hard, soft, i, j):
        if not (lo_i <= i <= hi_i and lo_j <= j <= hi_j and 0 <= i < g.nx and 0 <= j < g.ny):
            return None
        if hard[i, j] not in (FREE, net):
            return None
        o = int(soft[i, j])
        if o in (FREE, net):
            return 0.0
        if price is None:  # no ripping: routed copper is as fixed as the rest
            return None
        return RIP_COST * (1 + max(price.get(o, 0.0), 0.0)) if o != BLOCKED else RIP_COST * 4

    best, parent, heap = {}, {}, []
    for c in src:
        best[c] = 0.0
        heapq.heappush(heap, (h(c[1], c[2]), 0.0, c))
    moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0)]
    moves += [(a, b, math.sqrt(2)) for a in (1, -1) for b in (1, -1)]
    while heap:
        _, cost, c = heapq.heappop(heap)
        if cost > best.get(c, 1e18):
            continue
        layer, i, j = c
        if to_via:
            extra = step_cost(g.hard_via, g.soft_via, i, j)
            if extra == 0.0 and c not in src:
                path = [c]
                while path[-1] in parent:
                    path.append(parent[path[-1]])
                return path[::-1]
        elif c in dst:
            path = [c]
            while path[-1] in parent:
                path.append(parent[path[-1]])
            return path[::-1]
        steps = []
        for di, dj, w in moves:
            q = (layer, i + di, j + dj)
            extra = 0.0 if (not to_via and q in dst) else step_cost(g.hard[layer], g.soft[layer], i + di, j + dj)
            if extra is not None:
                steps.append((q, w + extra))
        extra = step_cost(g.hard_via, g.soft_via, i, j)
        if extra is not None:
            steps += [((n, i, j), VIA_COST + extra) for n in ROUTING if n != layer]
        for q, w in steps:
            nc = cost + w
            if nc < best.get(q, 1e18):
                best[q] = nc
                parent[q] = c
                heapq.heappush(heap, (nc + h(q[1], q[2]), nc, q))
    return None


def path_copper(g: Grid, path: list) -> tuple[list, list]:
    """The path as track pieces [(layer, a, b)] and via spots [(x, y)]."""
    runs, run = [], [path[0]]
    for c in path[1:]:
        if c[0] != run[-1][0]:
            runs.append(run)
            run = [c]
        else:
            run.append(c)
    runs.append(run)
    tracks, vias = [], []
    for k, run in enumerate(runs):
        corners = [run[0]]
        for a, m, c in zip(run, run[1:], run[2:], strict=False):
            if (m[1] - a[1], m[2] - a[2]) != (c[1] - m[1], c[2] - m[2]):
                corners.append(m)
        if len(run) > 1:
            corners.append(run[-1])
        for a, c in itertools.pairwise(corners):
            tracks.append((a[0], g.at(a[1], a[2]), g.at(c[1], c[2])))
        if k + 1 < len(runs):
            vias.append(g.at(run[-1][1], run[-1][2]))
    return tracks, vias


def rip(g: Grid, net: int, tracks: list, vias: list, whole_stubs: bool = False) -> set[int]:
    """Remove other nets' routed copper too close to the new copper; returns their nets. With
    `whole_stubs` (on the unrouted board), the rest of each removed piece's fanout stub goes too: a
    stub left without its via is fixed copper the router cannot join."""
    hit, keep, gone = set(), [], []
    for item in g.copper:
        o, name, layer, p0, p1, r, _drill = item
        near = False
        if o != net and not protected(name):
            if layer is None:
                c = p0
                near = any(_seg_seg(a, b, c, c) < g.clear + WIDTH / 2 + r + HOLE_MARGIN + SLACK for _, a, b in tracks)
                near = near or any(math.dist(v, c) < g.via_d + g.clear + HOLE_MARGIN + SLACK for v in vias)
            else:
                near = any(lay == layer and _seg_seg(a, b, p0, p1) < g.clear + WIDTH / 2 + r + SLACK for lay, a, b in tracks)
                near = near or any(_seg_dist(p0, p1, v) < g.clear + g.via_d / 2 + r + HOLE_MARGIN + SLACK for v in vias)
        if near:
            hit.add(o)
            gone.append(item)
        else:
            keep.append(item)
    while whole_stubs and gone:  # pieces of the same net sharing an end with a removed one
        ends = {(it[0], round(q[0], 3), round(q[1], 3)) for it in gone for q in (it[3], it[4])}
        gone = [it for it in keep if not protected(it[1])
                and any((it[0], round(q[0], 3), round(q[1], 3)) in ends for q in (it[3], it[4]))]
        keep = [it for it in keep if it not in gone]
    g.copper = keep
    return hit


def _seg_seg(a, b, c, d) -> float:
    """Distance between segments ab and cd."""
    return min(_seg_dist(a, b, c), _seg_dist(a, b, d), _seg_dist(c, d, a), _seg_dist(c, d, b)) if not _cross(
        a, b, c, d
    ) else 0.0


def _cross(a, b, c, d) -> bool:
    def o(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    return o(a, b, c) * o(a, b, d) < 0 and o(c, d, a) * o(c, d, b) < 0


def draw(g: Grid, net: int, tracks: list, vias: list) -> None:
    name = g.names[net]
    for layer, a, c in tracks:
        g.copper.append([net, name, layer, a, c, WIDTH / 2, 0.0])
    for at in vias:
        g.copper.append([net, name, None, at, at, g.via_d / 2, g.via_drill])


def write_back(g: Grid) -> None:
    """Replace the board's tracks and vias with the finisher's copper."""
    b = g.board
    for t in list(b.GetTracks()):
        b.Remove(t)
    for net, _name, layer, a, c, r, drill in g.copper:
        if layer is None:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(pcbnew.FromMM(2 * r))
            v.SetDrill(pcbnew.FromMM(drill))
            v.SetNetCode(net)
            b.Add(v)
        else:
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(c[0]), pcbnew.FromMM(c[1])))
            t.SetWidth(pcbnew.FromMM(2 * r))
            t.SetLayer(g.layers[layer])
            t.SetNetCode(net)
            b.Add(t)


def clusters(g: Grid, net: int) -> list[set]:
    """The net's copper in pieces, largest first."""
    cells = own_cells(g, net)
    groups: dict = {}
    for c, k in cells.items():
        groups.setdefault(k, set()).add(c)
    return sorted(groups.values(), key=len, reverse=True)


def gnd_islands(board: pcbnew.BOARD, report: dict) -> list:
    """GND pads the DRC finds cut off from the rest: [(pad, (x, y))]."""
    out = []
    for entry in report.get("unconnected_items", []):
        for it in entry["items"]:
            item = board.ResolveItem(pcbnew.KIID(it["uuid"]))
            item = item.Cast() if item is not None else None
            if item is not None and item.Type() == pcbnew.PCB_PAD_T and item.GetNetname() == "GND":
                out.append((item, (it["pos"]["x"], it["pos"]["y"])))
    return out


def connect_free(g: Grid, net: int) -> bool:
    """Join every piece of the net through free cells only; True when it is one piece."""
    parts = clusters(g, net)
    while len(parts) > 1:
        path = search(g, net, parts[-1], set().union(*parts[:-1]), None, reach=6.0)
        if path is None:
            return False
        draw(g, net, *path_copper(g, path))
        g.rebuild()
        parts = clusters(g, net)
    return True


CAREFUL_TRIES = 8


def careful_connect(g: Grid, net: int, names: dict, price: dict) -> bool:
    """Join the net; where it must cross another net's copper, keep the crossing only if every net
    it displaces then rejoins through free cells. A failed try is undone in full, and the nets it
    displaced cost more next try, so the board never ends worse than it started."""
    snap = [list(c) for c in g.copper]
    if connect_free(g, net):
        print(f"  routed {names.get(net, net)} through free cells")
        return True
    g.copper = [list(c) for c in snap]
    g.rebuild()
    for _ in range(CAREFUL_TRIES):
        parts = clusters(g, net)
        path = search(g, net, parts[-1], set().union(*parts[:-1]), price, reach=6.0)
        if path is None:
            break
        tracks, vias = path_copper(g, path)
        ripped = rip(g, net, tracks, vias)
        draw(g, net, tracks, vias)
        g.rebuild()
        if connect_free(g, net) and all(connect_free(g, o) for o in sorted(ripped)):
            print(f"  routed {names.get(net, net)}, rerouting {sorted(names.get(o, o) for o in ripped)}")
            return True
        g.copper = [list(c) for c in snap]
        g.rebuild()
        for o in ripped:
            price[o] = price.get(o, 0.0) + 10.0
    print(f"  OPEN {names.get(net, net)}: no try kept")
    return False


def main(board_dir: Path, rip_up: bool = True, careful: bool = False) -> int:
    pcb_path = next(board_dir.glob("*.kicad_pcb"))
    report = json.loads((board_dir / "build" / "drc.json").read_text(encoding="utf-8"))
    board = pcbnew.LoadBoard(str(pcb_path))
    for z in board.Zones():  # a pour island with no pad on it is dead copper: drop it
        if not z.GetIsRuleArea():
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    names = {code: str(ni.GetNetname()) for code, ni in board.GetNetsByNetcode().items()}
    g = Grid(board)
    g.names = names
    queue: list[int] = []
    for entry in report.get("unconnected_items", []):
        item = board.ResolveItem(pcbnew.KIID(entry["items"][0]["uuid"]))
        item = item.Cast() if item is not None else None
        if item is not None and item.GetNetname() != "GND" and item.GetNetCode() not in queue:
            queue.append(item.GetNetCode())
    price: dict[int, float] = {}
    failed: set[int] = set()
    routes = 0
    if careful:
        failed = {n for n in queue if not careful_connect(g, n, names, price)}
        queue = []
    while queue and routes < MAX_ROUTES:
        net = queue.pop(0)
        parts = clusters(g, net)
        while len(parts) > 1 and routes < MAX_ROUTES:
            routes += 1
            src, dst = parts[-1], set().union(*parts[:-1])  # the smallest piece to the rest
            path = search(g, net, src, dst, price if rip_up else None, reach=6.0)
            if path is None:
                print(f"  OPEN {names.get(net, net)}: no path")
                failed.add(net)
                break
            tracks, vias = path_copper(g, path)
            ripped = rip(g, net, tracks, vias)
            draw(g, net, tracks, vias)
            for o in ripped:
                price[o] = price.get(o, 0.0) + RIP_GROWTH
                if o not in queue:
                    queue.append(o)
            print(f"  routed {names.get(net, net)}: {len(tracks)} tracks, {len(vias)} vias"
                  + (f"; ripped {sorted(names.get(o, o) for o in ripped)}" if ripped else ""))
            g.rebuild()
            parts = clusters(g, net)
    gnd = next(c for c, n in names.items() if n == "GND")
    for pad, pos in gnd_islands(board, report):
        src = {(n, *g.cell(*pos)) for n in ROUTING if pad.IsOnLayer(g.layers[n])}
        path = search(g, gnd, src, "via", {}, reach=2.0)
        if path is None:
            print(f"  OPEN GND pad {pad.GetParentFootprint().GetReference()}.{pad.GetNumber()}: no via spot")
            continue
        tracks, vias = path_copper(g, path)
        vias.append(g.at(path[-1][1], path[-1][2]))
        draw(g, gnd, tracks, vias)
        g.rebuild()
        print(f"  GND pad {pad.GetParentFootprint().GetReference()}.{pad.GetNumber()}: via at {vias[-1]}")
    write_back(g)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(str(pcb_path))
    left = [names.get(n, n) for n in sorted(failed)] + [names.get(n, n) for n in queue]
    print(f"finish: {routes} routes, open: {left or 'none'}; wrote {pcb_path}")
    return 0


PAD_RE = re.compile(r"Pad (\S+) \[(.+?)\] of (\S+)")
PRE_ROUNDS = 5
SMALL_NET = 6  # pads: a net this small is routed whole before FreeRouting; a larger one only at its open pads


def hard_list(report: dict, old: list) -> list:
    """The connections to route before FreeRouting: the old list, plus each net the DRC found open
    (GND aside), with the pads named in its open items."""
    spec = {e["net"]: set(e["pads"]) for e in old}
    for entry in report.get("unconnected_items", []):
        for it in entry["items"]:
            m = PAD_RE.match(it["description"])
            if m and m.group(2) != "GND":
                spec.setdefault(m.group(2), set()).add(f"{m.group(3)}.{m.group(1)}")
    return [{"net": n, "pads": sorted(p)} for n, p in spec.items()]


def preroute(board_dir: Path, report_path: Path) -> int:
    """Route the hard connections on the unrouted board (no ripping) and write prerouted.json for
    design.py, which adds them as fixed copper; FreeRouting then routes the rest around them."""
    out = board_dir / "prerouted.json"
    old = json.loads(out.read_text(encoding="utf-8"))["connections"] if out.is_file() else []
    hard = hard_list(json.loads(report_path.read_text(encoding="utf-8")), old)
    board = pcbnew.LoadBoard(str(next(board_dir.glob("*.kicad_pcb"))))
    names = {code: str(ni.GetNetname()) for code, ni in board.GetNetsByNetcode().items()}
    codes = {n: c for c, n in names.items()}
    g = Grid(board)
    g.names = names
    original = [list(c) for c in g.copper]
    pad_at = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            p = pad.GetPosition()
            pad_at[f"{fp.GetReference()}.{pad.GetNumber()}"] = (mm(p.x), mm(p.y))
    def attempt(order: list) -> list:
        """Preroute in this order from the unrouted board; returns the nets left open."""
        g.copper = [list(c) for c in original]
        FIXED.clear()
        g.rebuild()
        failed = []
        for spec in order:
            net = codes.get(spec["net"])
            if net is None:
                continue
            whole = sum(1 for pad in g.pads if pad["net"] == net) <= SMALL_NET
            for _ in range(SMALL_NET if whole else len(spec["pads"])):
                parts = clusters(g, net)
                if len(parts) < 2:
                    break
                if whole:
                    src = parts[-1]
                else:
                    todo = [pad_at[p] for p in spec["pads"] if p in pad_at]
                    src = None
                    for x, y in todo:
                        c = g.cell(x, y)
                        src = next((q for q in parts if any((n, *c) in q for n in ROUTING)), None)
                        if src is not None and src is not parts[0]:
                            break
                    if src is None or src is parts[0]:
                        break
                dst = set().union(*(q for q in parts if q is not src))
                path = search(g, net, src, dst, None, reach=6.0)
                ripped: set[int] = set()
                if path is None:  # boxed in by its neighbours' fanout: take their stubs, FreeRouting routes them
                    path = search(g, net, src, dst, {}, reach=6.0)
                    if path is None:
                        print(f"  OPEN {spec['net']}: no path")
                        failed.append(spec["net"])
                        break
                    ripped = rip(g, net, *path_copper(g, path), whole_stubs=True)
                tracks, vias = path_copper(g, path)
                draw(g, net, tracks, vias)
                FIXED.add(spec["net"])
                g.rebuild()
                print(f"  prerouted {spec['net']}: {len(tracks)} tracks, {len(vias)} vias"
                      + (f"; took the fanout of {sorted(names[o] for o in ripped)}" if ripped else ""))
        return failed

    order, best = list(hard), None
    for k in range(PRE_ROUNDS):  # a net left open goes first next round
        print(f"preroute round {k + 1}")
        failed = attempt(order)
        if best is None or len(failed) < len(best[0]):
            best = (failed, [list(c) for c in g.copper], list(order))
        if not failed:
            break
        order = [h for h in order if h["net"] in failed] + [h for h in order if h["net"] not in failed]
    failed, g.copper, hard = best
    print(f"preroute: best round leaves {failed or 'nothing'} open")
    before = {(n, layer, tuple(a), tuple(b)) for _c, n, layer, a, b, _r, _d in original}
    after = {(n, layer, tuple(a), tuple(b)) for _c, n, layer, a, b, _r, _d in g.copper}
    copper = [
        {"net": name.removeprefix("/"), "layer": layer, "a": a, "b": b}
        for _net, name, layer, a, b, _r, _d in g.copper
        if (name, layer, tuple(a), tuple(b)) not in before
    ]
    removed = sorted({(n.removeprefix("/"), layer, a, b) for n, layer, a, b in before - after}, key=str)
    removed = [{"net": n, "layer": layer, "a": a, "b": b} for n, layer, a, b in removed]
    out.write_text(json.dumps({"connections": hard, "copper": copper, "removed": removed}, indent=1) + "\n",
                   encoding="utf-8")
    print(f"preroute: {len(hard)} nets, {len(copper)} pieces; wrote {out}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--pre":  # finish.py --pre BOARD_DIR DRC_JSON
        sys.exit(preroute(Path(args[1]).resolve(), Path(args[2]).resolve()))
    rip_up = "--no-rip" not in args  # --no-rip: only paths through free copper, nothing routed moves
    careful = "--careful" in args  # --careful: a crossing is kept only if what it displaces rejoins
    args = [a for a in args if a not in ("--no-rip", "--careful")]
    sys.exit(main(Path(args[0] if args else Path(__file__).parent).resolve(), rip_up, careful))
