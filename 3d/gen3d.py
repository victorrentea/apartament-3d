"""plan.dxf -> apartament3d.html (Three.js, single file, data inlined).

walls    : PERETI closed polylines, extruded to WALL_H
openings : gaps between wall pieces, found geometrically (an end face of a wall facing another wall face
           0.4..2.0 m away, spans overlapping); a gap with FERESTRE ink and no USI ink is a window
           (sill + lintel + glass), anything else is a door/passage (lintel only)
floor    : footprint = everything not reachable from outside once walls, gaps and rails are rasterised
usage    : .venv/bin/python gen3d.py [plan.dxf] [out.html]
"""
import base64, io, json, math, sys
from pathlib import Path
import ezdxf
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / 'workspace/apartament-3d/plan.dxf')
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).with_name('apartament3d.html'))
WALL_H, DOOR_H, SILL_H, WIN_H, RAIL_H = 2.70, 2.10, 0.90, 2.10, 1.00

msp = ezdxf.readfile(SRC).modelspace()


def pts(e):
    if e.dxftype() == 'LWPOLYLINE':
        return [(float(x), float(y)) for x, y in e.get_points('xy')]
    if e.dxftype() == 'LINE':
        return [tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]]
    if e.dxftype() == 'ARC':                       # doors may become LINE+ARC
        return [tuple(v)[:2] for v in e.flattening(0.01)]
    return []


def layer(name):
    return [p for e in msp.query(f'*[layer=="{name}"]') if (p := pts(e))]


walls = [p for e in msp.query('LWPOLYLINE[layer=="PERETI"]') if (p := pts(e))]
windows, doors, rails, other = layer('FERESTRE'), layer('USI'), layer('BALUSTRADE'), layer('ALTE')

# ---------------------------------------------------------------- wall faces
faces = []           # (axis, coord, lo, hi, normal_sign, length, convex_ends)
segs = []            # every wall face as drawn: (x0, y0, x1, y1, nx, ny) with outward normal
for loop in walls:
    a = sum(loop[i][0] * loop[i - 1][1] - loop[i - 1][0] * loop[i][1] for i in range(len(loop)))
    orient = 1 if a < 0 else -1     # sum above is -2*signed area
    n = len(loop)
    for i in range(n):
        (x0, y0), (x1, y1) = loop[i], loop[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        nx, ny = orient * dy, -orient * dx          # outward normal
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        segs.append((x0, y0, x1, y1, nx / L, ny / L))
        # a corner is convex when the neighbouring edge runs back into the wall (against the normal)
        pv, nv = loop[i - 1], loop[(i + 2) % n]
        convex = ((pv[0] - x0) * nx + (pv[1] - y0) * ny < 0) + ((nv[0] - x1) * nx + (nv[1] - y1) * ny < 0)
        if abs(dx) < 1e-6:     # vertical edge: x = const, normal along x
            faces.append(('x', x0, min(y0, y1), max(y0, y1), 1 if nx > 0 else -1, L, convex))
        elif abs(dy) < 1e-6:
            faces.append(('y', y0, min(x0, x1), max(x0, x1), 1 if ny > 0 else -1, L, convex))


def ink_in(polys, rect, pad):
    x0, y0, x1, y1 = rect
    return sum(1 for p in polys for (x, y) in p if x0 - pad <= x <= x1 + pad and y0 - pad <= y <= y1 + pad)


# ---------------------------------------------------------------- floor footprint (raster, 2 cm)
allx = [x for p in walls + rails for x, _ in p]
ally = [y for p in walls + rails for _, y in p]
X0, Y0, X1, Y1 = min(allx) - 0.5, min(ally) - 0.5, max(allx) + 0.5, max(ally) + 0.5
RES = 0.01                                     # 1 cm: fine enough for parquet planks
Wpx, Hpx = int((X1 - X0) / RES) + 1, int((Y1 - Y0) / RES) + 1
to_px = lambda x, y: ((x - X0) / RES, (Y1 - y) / RES)

# ---------------------------------------------------------------- openings, taken from the plan itself
# doors: hinge -> closed position of every door arc; windows: the extent of each group of window lines.
# Across the wall, an opening spans the thickness of the jambs on both sides.
wimg = Image.new('L', (Wpx, Hpx), 0); wdr = ImageDraw.Draw(wimg)
for loop in walls:
    wdr.polygon([to_px(*p) for p in loop], fill=255)
walls_r = np.asarray(wimg) > 0


def wall_at(x, y):
    px_, py_ = to_px(x, y); i, j = int(py_), int(px_)
    return 0 <= i < Hpx and 0 <= j < Wpx and walls_r[i, j]


def opening(a, b, kind):
    a, b = np.array(a, float), np.array(b, float)
    u = (b - a) / np.hypot(*(b - a)); n = np.array([-u[1], u[0]])
    los, his = [], []
    for p in (a - u * 0.02, b + u * 0.02):          # the jamb profile right at the edge of the opening
        if not wall_at(*p): continue
        lo = hi = 0.0
        while lo > -0.45 and wall_at(*(p + n * (lo - 0.005))): lo -= 0.005
        while hi < 0.45 and wall_at(*(p + n * (hi + 0.005))): hi += 0.005
        off = np.dot(p - a, n)
        los.append(off + lo); his.append(off + hi)
    # as thick as the thicker jamb, so no notch is left in the parapet / lintel band
    lo, hi = (min(los), max(his)) if los else (-0.08, 0.08)
    a, b = a - u * 0.03, b + u * 0.03                 # 3 cm into each jamb: no hairline leak
    pts_ = [a + n * lo, a + n * hi, b + n * lo, b + n * hi]
    xs_, ys_ = [p[0] for p in pts_], [p[1] for p in pts_]
    return {'r': [round(min(xs_), 4), round(min(ys_), 4), round(max(xs_), 4), round(max(ys_), 4)],
            'k': kind, 'axis': 'x' if abs(u[0]) > abs(u[1]) else 'y'}


gaps = []
leaf_lines = [pts(e) for e in msp.query('LINE[layer=="USI"]')]
for e in msp.query('ARC[layer=="USI"]'):
    c = np.array([e.dxf.center.x, e.dxf.center.y])
    ends = [np.array([e.start_point.x, e.start_point.y]), np.array([e.end_point.x, e.end_point.y])]
    dtip = [min(np.hypot(*(np.array(l[1]) - p)) for l in leaf_lines) for p in ends]
    closed = ends[1] if dtip[0] < dtip[1] else ends[0]
    gaps.append(opening(c, closed, 'door'))
segs_w = []
for e in msp.query('LINE[layer=="FERESTRE"]'):
    (x0, y0), (x1, y1) = pts(e)
    if math.hypot(x1 - x0, y1 - y0) > 0.2 and abs(x1 - x0) < 0.02: segs_w.append((x0, y0, x1, y1))   # frame lines, not the end caps
groups = []
for sgm in segs_w:
    for grp in groups:
        if any(abs(sgm[0] - o[0]) < 0.4 and min(max(sgm[1], sgm[3]), max(o[1], o[3])) > max(min(sgm[1], sgm[3]), min(o[1], o[3])) for o in grp):
            grp.append(sgm); break
    else:
        groups.append([sgm])
for grp in groups:
    xm = sum((s_[0] + s_[2]) / 2 for s_ in grp) / len(grp)
    ya = min(min(s_[1], s_[3]) for s_ in grp); yb = max(max(s_[1], s_[3]) for s_ in grp)
    gaps.append(opening((xm, ya), (xm, yb), 'window'))
img = Image.new('L', (Wpx, Hpx), 0)
dr = ImageDraw.Draw(img)
for loop in walls:
    dr.polygon([to_px(*p) for p in loop], fill=255)
for g in gaps:
    x0, y0, x1, y1 = g['r']
    dr.rectangle([to_px(x0, y1), to_px(x1, y0)], fill=255)
def extended(p, ext=0.08):
    """A rail polyline with both ends pushed 8 cm on, so it really closes against the wall it ends on."""
    p = [np.array(q, float) for q in p]
    for e_, nb in ((0, 1), (-1, -2)):
        d = p[e_] - p[nb]; L = np.hypot(*d)
        if L > 0: p[e_] = p[e_] + d / L * ext
    return [tuple(q) for q in p]


for p in rails:
    dr.line([to_px(*q) for q in extended(p)], fill=255, width=12)   # 12 cm: seals the balconies against the outside
barrier = np.asarray(img) > 0
outside, _ = nd.label(~barrier)
outside = outside == outside[0, 0]
inside = ~outside                                      # rooms + walls + balconies (walls stand on it)
if __import__('os').environ.get('DEBUG3D'):
    dbg = np.zeros(barrier.shape + (3,), np.uint8); dbg[outside] = (255, 200, 200); dbg[barrier] = (0, 0, 0); dbg[inside & ~barrier] = (255, 255, 255)
    Image.fromarray(dbg).resize((Wpx // 2, Hpx // 2)).save(__import__('os').environ['DEBUG3D'])
# rooms: free floor split by walls, closed openings and rails; named by where the survey puts each number
PX, PY, PPM = 20, 1175, 34.6                           # screenshot px -> metres (same mapping as the plan)
LABEL = {1: (292, 784), 2: (257, 651), 3: (202, 1000), 4: (202, 1104), 5: (206, 894), 6: (357, 638), 7: (294, 1116),
         8: (361, 873), 9: (319, 1069), 10: (368, 712), 11: (298, 1003), 12: (335, 706), 13: (181, 812), 14: (121, 1057)}
# close every door (hinge -> both arc ends) and every window/partition line, so each room is its own region
rimg = Image.fromarray((barrier * 255).astype(np.uint8)); rdr = ImageDraw.Draw(rimg)
for e in msp.query('ARC[layer=="USI"]'):
    c = e.dxf.center
    for v in (e.start_point, e.end_point):
        d = np.array([v.x - c.x, v.y - c.y]); d /= np.hypot(*d)
        a_, b_ = np.array([c.x, c.y]) - d * 0.12, np.array([v.x, v.y]) + d * 0.12
        rdr.line([to_px(*a_), to_px(*b_)], fill=255, width=3)
for p in windows + other:
    rdr.line([to_px(*q) for q in p], fill=255, width=3)
room_barrier = np.asarray(rimg) > 0
lab, _ = nd.label(~room_barrier)
room_of = {}
for k, (sx_, sy_) in LABEL.items():
    px_, py_ = to_px((sx_ - PX) / PPM, (PY - sy_) / PPM)
    l = lab[int(py_), int(px_)]
    if l and l not in room_of: room_of[l] = k
room_map = np.vectorize(lambda l: room_of.get(l, 0))(lab)


def room_at(x, y):
    px_, py_ = to_px(x, y)
    i, j = int(py_), int(px_)
    return int(room_map[i, j]) if 0 <= i < Hpx and 0 <= j < Wpx else 0


wall_faces = []
for x0, y0, x1, y1, nx, ny in segs:
    mx, my = (x0 + x1) / 2 + nx * 0.06, (y0 + y1) / 2 + ny * 0.06
    k = room_at(mx, my)
    if k == 0 and math.hypot(x1 - x0, y1 - y0) < 0.45:     # jamb / reveal inside an opening: plain white
        px_, py_ = to_px(mx, my)
        if 0 <= int(py_) < Hpx and 0 <= int(px_) < Wpx and inside[int(py_), int(px_)]: k = -1
    wall_faces.append([round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4), k])

# ---------------------------------------------------------------- walls in three height bands
# 0 -> sill: walls + window openings (parapets); sill -> door head: walls only; door head -> top: walls + every opening
# Each band is traced as continuous outlines, so a lintel is part of the wall, not a box stuck on it.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from vectorize import trace, merge                     # same pixel-edge tracer as the 2D plan

def rect_mask(kinds):
    im = Image.new('L', (Wpx, Hpx), 0); d_ = ImageDraw.Draw(im)
    for gp in gaps:
        if gp['k'] in kinds:
            x0, y0, x1, y1 = gp['r']
            d_.rectangle([to_px(x0, y1), to_px(x1, y0)], fill=255)
    return np.asarray(im) > 0


def to_m(px_, py_):
    return X0 + px_ * RES, Y1 - py_ * RES


BANDS = [(0.0, SILL_H, walls_r | rect_mask({'window'})), (SILL_H, DOOR_H, walls_r),
         (DOOR_H, WALL_H, walls_r | rect_mask({'window', 'door'}))]
band_faces, top_loops = [], []
for h0, h1, mask in BANDS:
    for loop in trace(mask):
        loop = merge(loop)
        pts_m = [to_m(*p) for p in loop]
        n = len(pts_m)
        for i in range(n):
            (x0, y0), (x1, y1) = pts_m[i], pts_m[(i + 1) % n]
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 1e-6: continue
            nx, ny = (y1 - y0) / L, -(x1 - x0) / L
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            px_, py_ = to_px(mx + nx * 0.015, my + ny * 0.015)
            if 0 <= int(py_) < Hpx and 0 <= int(px_) < Wpx and mask[int(py_), int(px_)]: nx, ny = -nx, -ny   # normal must leave the wall
            k = room_at(mx + nx * 0.06, my + ny * 0.06)
            if k == 0 and L < 0.45:
                px_, py_ = to_px(mx + nx * 0.06, my + ny * 0.06)
                if 0 <= int(py_) < Hpx and 0 <= int(px_) < Wpx and inside[int(py_), int(px_)]: k = -1   # reveal in an opening
            band_faces.append([round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4), k, h0, h1])
        if h1 == WALL_H:
            top_loops.append([[round(x, 4), round(y, 4)] for x, y in pts_m])


def ring_area(l):
    return sum(l[i - 1][0] * l[i][1] - l[i][0] * l[i - 1][1] for i in range(len(l))) / 2


def in_ring(x, y, l):
    c = False
    for i in range(len(l)):
        (xi, yi), (xj, yj) = l[i], l[i - 1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
    return c


# caps on top: outer outlines with their holes (the top band closes rings around rooms)
outers = sorted([l for l in top_loops], key=lambda l: -abs(ring_area(l)))
caps = []
for l in outers:
    host = next((c for c in caps if abs(ring_area(c['o'])) > abs(ring_area(l)) and in_ring(l[0][0] + 1e-4, l[0][1] + 1e-4, c['o'])
                 and not any(in_ring(l[0][0] + 1e-4, l[0][1] + 1e-4, h) for h in c['h'])), None)
    if host: host['h'].append(l)
    else: caps.append({'o': l, 'h': []})

# lintels and sills: their two long sides are finished like the room each one faces
gap_faces = []
for gp in gaps:
    x0, y0, x1, y1 = gp['r']
    if gp['axis'] == 'x':
        sides = [((x0, y0, x1, y0), (0, -1)), ((x0, y1, x1, y1), (0, 1))]
    else:
        sides = [((x0, y0, x0, y1), (-1, 0)), ((x1, y0, x1, y1), (1, 0))]
    spans = [(DOOR_H if gp['k'] == 'door' else WIN_H, WALL_H)] + ([(0.0, SILL_H)] if gp['k'] == 'window' else [])
    for (a0, b0, a1, b1), (nx, ny) in sides:
        k = room_at((a0 + a1) / 2 + nx * 0.08, (b0 + b1) / 2 + ny * 0.08)
        for h0, h1 in spans:
            gap_faces.append([round(a0, 4), round(b0, 4), round(a1, 4), round(b1, 4), k, h0, h1, nx, ny])

KIND = {5: 'tile', 6: 'tile', 7: 'tile', 13: 'stone', 14: 'stone'}
yy, xx = np.mgrid[0:Hpx, 0:Wpx]
rng = np.random.default_rng(7)
# parquet: 12 cm planks along x, staggered 1.2 m boards, each board its own oak tone, thin dark joints
pw, pl = 12, 120
row = yy // pw
board = (xx + (row * 37) % pl) // pl
tone = rng.uniform(-18, 18, size=(row.max() + 2, board.max() + 2))[row, board]
grain = (np.sin(xx * 0.9 + row * 1.7) * 3).astype(float)
par = np.stack([196 + tone + grain, 160 + tone * 0.8 + grain, 118 + tone * 0.6 + grain], -1)
joint = (yy % pw == 0) | ((xx + (row * 37) % pl) % pl == 0)
par[joint] = (120, 92, 64)
# tiles 30 cm (bathrooms, kitchen) and 40 cm stone slabs (balconies)
tile = np.full((Hpx, Wpx, 3), (226, 224, 216), float); tile[(xx % 30 == 0) | (yy % 30 == 0)] = (170, 168, 160)
stone = np.full((Hpx, Wpx, 3), (176, 172, 164), float); stone[(xx % 40 == 0) | (yy % 40 == 0)] = (130, 126, 120)
rgb = par
for k, kind in KIND.items():
    sel = ((room_map == k) | (nd.binary_dilation(room_map == k, iterations=16) & room_barrier))   # tiles run on under the door threshold
    rgb[sel] = (tile if kind == 'tile' else stone)[sel]
rgba = np.zeros((Hpx, Wpx, 4), np.uint8)
rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
rgba[..., 3] = np.where(inside, 255, 0)
# ceiling: over the rooms only (not over the balconies)
ceil = np.where(nd.binary_dilation(np.isin(room_map, list(range(1, 13))), iterations=30) & inside, 255, 0).astype(np.uint8)   # rooms + 30 cm into their walls
cbuf = io.BytesIO(); Image.fromarray(ceil, 'L').save(cbuf, 'PNG', optimize=True)
ceil_png = base64.b64encode(cbuf.getvalue()).decode()


def to_plan(i, j):
    return X0 + j * RES, Y1 - i * RES


# a ceiling light in every room (at the room's most central point)
lamps = []
BATH = (6, 7)                                  # bathrooms get wall sconces instead of a pendant
SCONCE_ROOMS = {6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 2, 12: 1}   # room -> how many of its longest walls get sconces (hall, closets too)
room_pts = {}                                  # the most central floor point of every room (walk-through / checks)
for k in range(1, 15):
    reg = room_map == k
    if reg.any():
        dd = nd.distance_transform_edt(reg); i, j = np.unravel_index(np.argmax(dd), dd.shape)
        room_pts[k] = [round(v, 3) for v in to_plan(i, j)]
# gallery viewpoints: the corners of every room worth a photo, 35 cm off the walls, looking at the room's centre
views = []
for k in (1, 2, 3, 4, 5, 6, 7, 11, 13, 14):
    reg = room_map == k
    if not reg.any(): continue
    dd = nd.distance_transform_edt(reg)
    for off in (0.35, 0.22):
        ii, jj = np.nonzero(dd >= off / RES)
        if len(ii): break
    if not len(ii): continue
    ci, cj = np.argwhere(reg).mean(0)
    seen = []
    for si, sj in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        n = np.argmax(si * ii + sj * jj); p = to_plan(ii[n], jj[n])
        if any(math.hypot(p[0] - q[0], p[1] - q[1]) < 0.8 for q in seen): continue      # narrow room: two corners coincide
        seen.append(p); t = to_plan(ci, cj)
        views.append([k, round(p[0], 3), round(p[1], 3), round(t[0], 3), round(t[1], 3)])
for k in range(1, 13):
    if k in SCONCE_ROOMS: continue
    reg = room_map == k
    if not reg.any(): continue
    dd = nd.distance_transform_edt(reg)
    i, j = np.unravel_index(np.argmax(dd), dd.shape)
    lamps.append([*map(lambda v: round(v, 3), to_plan(i, j)), k])

# a light switch beside every door, on the handle side, on the face of the room the door opens into
wimg = Image.new('L', (Wpx, Hpx), 0); wdr = ImageDraw.Draw(wimg)
for loop in walls:
    wdr.polygon([to_px(*p) for p in loop], fill=255)
walls_r = np.asarray(wimg) > 0                         # real walls only (a window gap is not a wall to put a switch on)
def wall_at(x, y):
    px_, py_ = to_px(x, y); i, j = int(py_), int(px_)
    return 0 <= i < Hpx and 0 <= j < Wpx and walls_r[i, j]
switches = []
door_leaves = []      # [hinge x, hinge y, width, closed angle, drawn (ajar) angle]  plan radians
arcs = list(msp.query('ARC[layer=="USI"]'))
leaves = [pts(e) for e in msp.query('LINE[layer=="USI"]')]
for e in arcs:
    c = np.array([e.dxf.center.x, e.dxf.center.y])
    ends = [np.array([e.start_point.x, e.start_point.y]), np.array([e.end_point.x, e.end_point.y])]
    # the leaf tip is the arc end that a leaf line touches; the other end is where the door closes
    tips = [min(np.hypot(*(np.array(l[1]) - p)) for l in leaves) for p in ends]
    tip, closed = (ends[0], ends[1]) if tips[0] < tips[1] else (ends[1], ends[0])
    mid = (c + closed) / 2; nn = np.array([-(closed - c)[1], (closed - c)[0]]); nn /= np.hypot(*nn)
    # door kind: 1 = balcony door (PVC + glass), 2 = bathroom door (wood, small frosted light), 3 = entrance door (solid), 0 = wooden room door
    sides = [{room_at(*(mid + nn * sgn * dd)) for dd in (0.3, 0.45, 0.6)} - {0} for sgn in (1, -1)]
    both = sides[0] | sides[1]
    glazed = 1 if both & {13, 14} else 2 if both & {6, 7} else 3 if (not sides[0] or not sides[1]) else 0
    door_leaves.append([round(c[0], 4), round(c[1], 4), round(float(e.dxf.radius), 4),
                        round(math.atan2(closed[1] - c[1], closed[0] - c[0]), 4), round(math.atan2(tip[1] - c[1], tip[0] - c[0]), 4), glazed, int(glazed == 3 or 8 in both)])
    u = (closed - c) / np.hypot(*(closed - c))
    side = tip - c - u * np.dot(tip - c, u); side /= np.hypot(*side)      # towards the room the door opens into
    p = closed + u * 0.18                                                  # into the jamb, 18 cm past the opening
    if not wall_at(*p): continue
    for k_ in range(1, 60):
        q = p + side * k_ * 0.01
        if not wall_at(*q):
            room = room_at(*(q + side * 0.05))
            if room and room not in (13, 14):
                switches.append([round(q[0], 3), round(q[1], 3), round(side[0], 3), round(side[1], 3)])
            break

# sockets: on the two longest faces of every room, 30 cm above the floor, a third along the face
# bathroom wall sconces: two on the longest face of each bathroom, 1.95 m up (above where the mirror goes)
sconces = []
for k, nwalls in SCONCE_ROOMS.items():
    fs = []
    for x0, y0, x1, y1, nx, ny in segs:
        if room_at((x0 + x1) / 2 + nx * 0.06, (y0 + y1) / 2 + ny * 0.06) == k:
            fs.append((math.hypot(x1 - x0, y1 - y0), x0, y0, x1, y1, nx, ny))
    for L, x0, y0, x1, y1, nx, ny in sorted(fs, reverse=True)[:nwalls]:
      for t_ in ((0.5,) if L < 0.9 else (0.3, 0.7)):
        sconces.append([round(x0 + (x1 - x0) * t_ + nx * 0.004, 3), round(y0 + (y1 - y0) * t_ + ny * 0.004, 3), round(nx, 3), round(ny, 3)])

sockets = []
for k in BATH:
    sc = [q for q in sconces if room_at(q[0] + q[2] * 0.1, q[1] + q[3] * 0.1) == k]
    if sc:
        x, y, nx, ny = sc[0]
        tx, ty = -ny, nx                                   # along the wall
        sockets.append([round(x + tx * 0.45, 3), round(y + ty * 0.45, 3), nx, ny, 1.10])
by_room = {}
for x0, y0, x1, y1, nx, ny in segs:
    L = math.hypot(x1 - x0, y1 - y0)
    k = room_at((x0 + x1) / 2 + nx * 0.06, (y0 + y1) / 2 + ny * 0.06)
    if k and k not in (6, 7, 9, 10, 13, 14) and L >= 0.9:
        by_room.setdefault(k, []).append((L, x0, y0, x1, y1, nx, ny))
for k, fs in by_room.items():
    for L, x0, y0, x1, y1, nx, ny in sorted(fs, reverse=True)[:2 if k not in (1, 11) else 3]:
        x, y = x0 + (x1 - x0) / 3, y0 + (y1 - y0) / 3
        sockets.append([round(x + nx * 0.004, 3), round(y + ny * 0.004, 3), round(nx, 3), round(ny, 3), 0.30])
buf = io.BytesIO()
Image.fromarray(rgba, 'RGBA').save(buf, 'PNG', optimize=True)
floor_png = base64.b64encode(buf.getvalue()).decode()
floor_area = (inside & ~barrier).sum() * RES * RES
dist = nd.distance_transform_edt(inside & ~barrier)          # walk mode starts in the roomiest spot
sy, sx = np.unravel_index(np.argmax(dist), dist.shape)
start = [round(X0 + sx * RES, 3), round(Y1 - sy * RES, 3)]

data = {
    'H': {'wall': WALL_H, 'door': DOOR_H, 'sill': SILL_H, 'win': WIN_H, 'rail': RAIL_H},
    'walls': [[[round(x, 4), round(y, 4)] for x, y in l] for l in walls],
    'faces': wall_faces, 'gapFaces': gap_faces, 'bandFaces': band_faces, 'caps': caps,
    'roomPts': room_pts, 'views': views, 'doors': door_leaves, 'lamps': lamps, 'sconces': sconces, 'switches': switches, 'sockets': sockets, 'ceiling': ceil_png,
    'gaps': gaps,
    'rails': [[[round(x, 4), round(y, 4)] for x, y in p] for p in rails if len(p) >= 2],
    'start': start,
    'floor': {'png': floor_png, 'x0': X0, 'y0': Y0, 'x1': X1, 'y1': Y1},
}
print(f'sconces {len(sconces)}, lamps {len(lamps)}, switches {len(switches)}, sockets {len(sockets)}')
print(f'walls {len(walls)} loops, gaps: {sum(g["k"] == "door" for g in gaps)} doors, '
      f'{sum(g["k"] == "window" for g in gaps)} windows; floor footprint {floor_area:.1f} m2')
for g in gaps:
    print('  ', g['k'], g['r'], f'{max(g["r"][2] - g["r"][0], g["r"][3] - g["r"][1]):.2f} m')

tpl = Path(__file__).with_name('template.html').read_text()
html = tpl.replace('/*__DATA__*/null', json.dumps(data, separators=(',', ':')))
# optional furniture blocks, one per furnished room, each made by its own script: furniture/<room>/furniture.html
fdir = Path(__file__).with_name('furniture')
blocks = sorted(fdir.glob('*/furniture.html')) + ([fdir / 'furniture.html'] if (fdir / 'furniture.html').exists() else [])
html = html.replace('<!--__FURNITURE__-->', '\n'.join(b.read_text() for b in blocks))
# product list (top-right drop-down): every furnished piece that has a shop link, grouped by room
import json as _json, html as _html
ROOM_NAMES = {'.': 'Dormitor (camera 2)', 'living': 'Living (camera 1)', 'bedroom3': 'Dormitor (camera 3)', 'bedroom4': 'Dormitor (camera 4)', 'balconies': 'Balcoane', 'extras': 'Hol și oficiu', 'bedroom3-extras': 'Dormitor (camera 3): gaming și decor', 'decor': 'Decor', 'bath6': 'Baie (camera 6)'}
plist, total, pmeta = '', 0, {}
for jf in sorted(fdir.glob('furniture.json')) + sorted(fdir.glob('*/furniture.json')):
    key = '.' if jf.parent == fdir else jf.parent.name
    seen = {}
    for p in _json.loads(jf.read_text()).get('pieces', []):
        if p.get('url'):
            e = seen.setdefault(p['url'], [p['product'], 0, [], p.get('price_lei')]); e[1] += 1; e[2].append(p['id'])
            pmeta[('furniture' if key == '.' else 'furniture-' + key) + '/' + p['id']] = {'name': p['product'], 'price': p.get('price_lei'), 'url': p['url']}
    if not seen: continue
    plist += f'<h4>{ROOM_NAMES.get(key, key)}</h4>'
    for url, (name, n, ids, price) in seen.items():
        total += n
        plist += f'<a href="{_html.escape(url)}" data-g="{'furniture' if key == '.' else 'furniture-' + key}" data-ids="{_html.escape(','.join(ids))}" target="_blank" rel="noopener">{_html.escape(name)}{f" <small>×{n}</small>" if n > 1 else ""}{f" <small>· {price:g} lei</small>" if price else ""}</a>'
# photo gallery: pictures taken from the room corners by 3d/gallery.mjs (re-run it after the furniture changes)
gal = Path(__file__).with_name('gallery') / 'index.json'
ghtml = ''
if gal.exists():
    GNAMES = {1: 'Living', 2: 'Dormitor 2', 3: 'Dormitor 3', 4: 'Dormitor 4', 5: 'Bucătărie', 6: 'Baie mare', 7: 'Baie mică', 11: 'Hol', 13: 'Balcon mic', 14: 'Balcon lung'}
    last = None
    for e in _json.loads(gal.read_text()):
        if e['room'] != last: ghtml += f'<h4>{GNAMES.get(e["room"], e["room"])}</h4>'; last = e['room']
        ghtml += f'<img loading="lazy" src="gallery/t_{e["file"]}" data-full="gallery/{e["file"]}" data-cam="{e["cam"]}" alt="{GNAMES.get(e["room"], "")}">'
    ghtml = f'<div id="gal">{ghtml}</div>'
html = html.replace('<!--__GALLERY__-->', ghtml)
html = html.replace('/*__PMETA__*/', 'const PMETA = ' + _json.dumps(pmeta, ensure_ascii=False) + ';')
html = html.replace('<!--__PRODUCTS__-->', f'<div id="prodwrap"><button id="daynight" title="Zi: lumina vine de afară, lustrele sunt stinse. Noapte: lustrele aprinse.">☀️ Zi</button><details id="prod"><summary>Produse ({total})</summary>{plist}</details></div>' if total else '')
print('furniture blocks:', [str(b.relative_to(fdir)) for b in blocks])
OUT.write_text(html)
print('wrote', OUT, f'{OUT.stat().st_size // 1024} KB')
