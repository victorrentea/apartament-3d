"""Step 2: vector plan from clean.png -> plan.svg, plan_varfuri.svg, plan.dxf, comparison images.

walls    : orthogonal polygons traced from wall_mask_clean.png (filled + outlined)
thin ink : thinned to 1px centre lines (Zhang-Suen), split into polylines, simplified, classified as
           window / door / rail / partition by where they are on the drawing
scale    : 34.6 px = 1 m (mean of 13 room dimensions of the survey, 34.2..35.1)
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd
import ezdxf
from ezdxf.enums import TextEntityAlignment
from vectorize import wall_loops

PX_PER_M = 34.6
clean = np.asarray(Image.open('clean.png').convert('L')).astype(int)
H, W = clean.shape
wall = np.asarray(Image.open('wall_mask_clean.png')) > 127
# peel the JPEG fringe: a wall-edge pixel less than half covered by ink (grey > 145) is not wall
edge = wall & ~nd.binary_erosion(wall)
wall &= ~(edge & (clean > 145))
# hand fixes, each checked against the original (blue dimension ticks / window frames glued to a wall face)
wall[855:861, 320:336] = False          # #7/#8 tick box under the room 1 / room 8 wall
wall[1085, 318:326] = False             # #11 step on the room 7 bottom wall face
wall[1082:1085, 326] = False
wall[1110:1114, 133:145] = False        # #12 window frame end on the room 4 wall end
# window openings: the wall stops where the hatch stops (rows read on the original), the rest is window frame
wall[655:658, 193:207] = False          # room 2 window, top   (hatch ends at row 654)
wall[700:703, 193:207] = False          # room 2 window, bottom (hatch resumes at row 703)
wall[760:764, 193:207] = False          # room 1 window, top   (hatch ends at row 759)
wall[997:1001, 132:146] = False         # room 3 side window, top (hatch ends at row 996)
# per-room review (one agent per room) + Victor's marks, each re-checked on the original's pixels
wall[678:683, 329:333] = False          # room 6: the 'nub' at the hinge is the start of the door leaf
wall[688:692, 315:320] = True           # room 12: wall stub under the blue 0.93/1.05 dimensions where room 2's door closes
wall[718:722, 319:323] = False          # room 12: the jamb pier is x 315-318, not 315-322
wall[722:729, 321:323] = False          # room 12: the bottom wall ends at x 320
wall[722, 319:321] = False              # room 12: pier right face at x 319 down to the bottom wall (Fable review)
wall[1082:1095, 273:277] = False        # room 7: the 'nib' at the top-left jamb is the door leaf + a dimension tick
wall[1096, 317:327] = False             # room 7: the recess under the wall stub is 4 rows deep, not 3
wall[855:859, 327:334] = True           # room 8: door jamb block under the wall (grey, not blue; Victor's mark)
ROI = (20, 585, 410, 1175)                     # x1, y1, x2, y2 of the drawing

# ---------------------------------------------------------------- walls
loops = wall_loops(wall)


def area(l):
    return abs(sum(l[i - 1][0] * l[i][1] - l[i][0] * l[i - 1][1] for i in range(len(l)))) / 2


loops = [l for l in loops if area(l) >= 12]

# ---------------------------------------------------------------- thin ink -> classes
ink = (clean < 190) & ~nd.binary_dilation(wall)
roi = np.zeros_like(ink); roi[ROI[1]:ROI[3], ROI[0]:ROI[2]] = True
ink &= roi

REMOVE = [(377, 603, 384, 609), (370, 706, 375, 718), (188, 760, 197, 798), (173, 804, 189, 820), (292, 1140, 299, 1146)]
RAIL = [(98, 944, 133, 1166), (157, 726, 193, 844)]
PARTITION = [(323, 722, 348, 730), (308, 1056, 312, 1086)]
WINDOW = [(193, 654, 206, 704), (193, 759, 205, 802), (133, 879, 151, 920), (132, 996, 145, 1015), (132, 1097, 145, 1115)]


def inside(x, y, boxes):
    return any(b[0] <= x < b[2] and b[1] <= y < b[3] for b in boxes)


lab, n = nd.label(ink, np.ones((3, 3)))
for i, sl in enumerate(nd.find_objects(lab), 1):
    comp = lab[sl] == i
    cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
    if comp.sum() < 6 or inside(cx, cy, REMOVE):
        ink[sl][comp] = False


def thin(img):
    """Zhang-Suen thinning."""
    img = np.pad(img.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            P = [np.roll(np.roll(img, -dy, 0), -dx, 1) for dy, dx in
                 ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))]
            B = sum(P)
            A = sum(((P[k] == 0) & (P[(k + 1) % 8] == 1)) for k in range(8))
            if step == 0:
                c = (P[0] * P[2] * P[4] == 0) & (P[2] * P[4] * P[6] == 0)
            else:
                c = (P[0] * P[2] * P[6] == 0) & (P[0] * P[4] * P[6] == 0)
            rm = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if rm.any():
                img[rm] = 0; changed = True
        if not changed:
            return img[1:-1, 1:-1].astype(bool)


skel = thin(ink)
NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def neighbours(p):
    y, x = p
    return [(y + dy, x + dx) for dy, dx in NB if 0 <= y + dy < H and 0 <= x + dx < W and skel[y + dy, x + dx]]


def polylines():
    pts = set(zip(*np.nonzero(skel)))
    deg = {p: len(neighbours(p)) for p in pts}
    used = set()
    out = []
    nodes = [p for p in pts if deg[p] != 2]
    for s in nodes:
        for q in neighbours(s):
            e = frozenset((s, q))
            if e in used: continue
            path = [s, q]; used.add(e)
            while deg[path[-1]] == 2:
                nxt = [r for r in neighbours(path[-1]) if frozenset((path[-1], r)) not in used]
                if not nxt: break
                used.add(frozenset((path[-1], nxt[0]))); path.append(nxt[0])
            out.append(path)
    # pure loops (no end / junction)
    seen = {p for e in used for p in e}
    for s in pts - seen:
        if s in seen: continue
        path = [s]; seen.add(s); cur = s
        while True:
            nxt = [r for r in neighbours(cur) if r not in seen]
            if not nxt: break
            cur = nxt[0]; path.append(cur); seen.add(cur)
        path.append(s); out.append(path)
    return out


def dp(points, eps=0.6):
    if len(points) < 3: return points
    a, b = np.array(points[0], float), np.array(points[-1], float)
    ab = b - a; L = np.hypot(*ab)
    best, idx = -1, 0
    for i in range(1, len(points) - 1):
        p = np.array(points[i], float)
        d = abs(ab[0] * (a[1] - p[1]) - ab[1] * (a[0] - p[0])) / L if L else np.hypot(*(p - a))
        if d > best: best, idx = d, i
    if best <= eps: return [points[0], points[-1]]
    return dp(points[:idx + 1], eps)[:-1] + dp(points[idx:], eps)


def classify(path):
    ys = [p[0] for p in path]; xs = [p[1] for p in path]
    cx, cy = sum(xs) / len(xs) + .5, sum(ys) / len(ys) + .5
    if inside(cx, cy, WINDOW): return 'window'
    if inside(cx, cy, RAIL): return 'rail'
    if inside(cx, cy, PARTITION): return 'partition'
    if inside(cx, cy, [(342, 698, 354, 723)]): return 'doorraw'   # closet 10's tiny folding door: keep as drawn
    return 'door'


lines = []      # (class, [(x, y), ...]) in pixel-centre coordinates
for path in polylines():
    if len(path) < 2: continue
    cls = classify(path)
    pts = [(x + .5, y + .5) for y, x in dp(path)]
    lines.append((cls, pts))

# ---------------------------------------------------------------- windows & doors, parametric
lines = [(c, p) for c, p in lines if c not in ('window', 'door', 'rail')]

# balcony rails, parametric (positions read on the original by the balcony reviewers):
# balcony 14 = two parallel U lines into the wall face x 133.5
rails = [[(133.5, 946.5), (99.5, 946.5), (99.5, 1164.5), (133.5, 1164.5)],
         [(133.5, 951.5), (104.5, 951.5), (104.5, 1158.5), (133.5, 1158.5)]]
# balcony 13 = vertical line from the bottom wall, a quarter circle, horizontal line into the wall face x 194.5;
# the corner radius is fitted to the drawing's rail pixels
rail_ink = skel.copy(); rail_ink[:, :] = False
rail_ink[726:845, 157:194] = ((clean < 200) & ~nd.binary_dilation(wall))[726:845, 157:194]
ys_, xs_ = np.nonzero(rail_ink); RP = np.c_[xs_ + .5, ys_ + .5]


def corner_path(xv, yh, R, y_bottom, x_wall, n=24):
    cx, cy = xv + R, yh + R
    pts = [(xv, y_bottom), (xv, cy)]
    for t in np.linspace(math.pi, 1.5 * math.pi, n)[1:-1]:
        pts.append((cx + R * math.cos(t), cy + R * math.sin(t)))
    pts += [(cx, yh), (x_wall, yh)]
    return pts


def dist_to_corner(P, xv, yh, R):
    cx, cy = xv + R, yh + R
    d = np.empty(len(P))
    for i, (x, y) in enumerate(P):
        if x <= cx and y <= cy:
            d[i] = abs(np.hypot(x - cx, y - cy) - R)
        elif y > cy:
            d[i] = abs(x - xv)
        else:
            d[i] = abs(y - yh)
    return d


for xv, yh in ((159.5, 727.5), (164.5, 733.5)):
    near = RP[np.minimum(np.abs(RP[:, 0] - xv), np.abs(RP[:, 1] - yh)) < 40]
    best = min(range(10, 40), key=lambda R: np.sum(dist_to_corner(near, xv, yh, R) < 0.8) * -1)
    rails.append([(round(x, 2), round(y, 2)) for x, y in corner_path(xv, yh, best, 845.0, 194.5)])
    print('balcony 13 rail corner radius', best, 'px')
lines += [('rail', r) for r in rails]


def extend_to_wall(pts, maxd=5):
    for end in (0, -1):
        p = np.array(pts[end], float); q = np.array(pts[1 if end == 0 else -2], float)
        d = p - q; L = np.hypot(*d)
        if L == 0: continue
        d /= L
        for k in range(1, maxd * 2 + 1):
            r = p + d * k * 0.5
            if wall[int(r[1]), int(r[0])]:
                pts[end] = (round(float(r[0]), 2), round(float(r[1]), 2)); break
    return pts


lines = [(c, extend_to_wall(list(p)) if c == 'partition' else p) for c, p in lines]
lines = [(c, p) for c, p in lines if c != 'doorraw' and not (c == 'partition' and min(y for _, y in p) > 718 and max(y for _, y in p) < 732)]
lines.append(('doorraw', [(351, 700.5), (345.3, 709.3), (347, 711.5), (345.3, 713.7), (351.5, 723)]))
lines.append(('doorraw', [(347, 711.5), (352, 711.5)]))
lines.append(('partition', [(321, 725.5), (323, 726.4), (325, 727.9), (326.5, 728.1), (328, 726.8), (329.5, 725.5), (331.5, 724.1),
                            (333, 725.3), (334.5, 726.6), (336.5, 728.1), (338, 727.6), (339.5, 726), (341, 724.2), (343, 724.2),
                            (344.5, 725.6), (346, 726.1), (348, 726)]))
wall_dist = nd.distance_transform_edt(~wall)

windows = []    # vertical window frame lines [(x, ytop), (x, ybot)]
for bx in WINDOW:
    n_before = len(windows)
    cols = np.arange(bx[0], bx[2])
    rows = [y for y in range(bx[1], bx[3]) if not wall[y, bx[0]:bx[2]].any()]
    sub = clean[np.ix_(rows, cols)] < 170
    prof = sub.mean(0)
    on = prof > 0.5
    k = 0
    while k < len(cols):
        if not on[k]: k += 1; continue
        j = k
        while j + 1 < len(cols) and on[j + 1]: j += 1
        xs_ = cols[k:j + 1]; w_ = prof[k:j + 1]
        gx = float((xs_ * w_).sum() / w_.sum()) + .5
        dark_rows = [rows[i] for i in range(len(rows)) if sub[i, k:j + 1].any()]
        top, bot = min(dark_rows), max(dark_rows) + 1
        col = wall[:, int(gx)]
        for d_ in range(0, 6):                       # snap the ends onto the wall faces
            if col[top - 1 - d_]: top = top - d_; break
        for d_ in range(0, 6):
            if col[bot + d_]: bot = bot + d_; break
        windows.append([(gx, float(top)), (gx, float(bot))])
        k = j + 1
    grp = windows[n_before:]
    if len(grp) >= 2:
        xa, xb = min(w_[0][0] for w_ in grp), max(w_[0][0] for w_ in grp)
        ya, yb = min(w_[0][1] for w_ in grp), max(w_[1][1] for w_ in grp)
        xm = int((xa + xb) / 2)
        if not wall[int(ya) - 1, xm]: windows.append([(xa, ya + .5), (xb, ya + .5)])
        if not wall[int(yb), xm]: windows.append([(xa, yb - .5), (xb, yb - .5)])

DOORS = [(332, 668, 353, 682), (296, 686, 322, 724), (194, 764, 221, 830), (284, 832, 314, 851),
         (311, 860, 329, 888), (250, 885, 270, 915), (311, 969, 330, 999), (133, 1000, 161, 1039), (250, 1014, 270, 1044),
         (250, 1059, 269, 1087), (132, 1071, 160, 1114), (276, 1090, 305, 1109)]
door_ink = (clean < 200) & ~nd.binary_dilation(wall) & roi
for bx in WINDOW:
    door_ink[bx[1]:bx[3], bx[0]:bx[2]] = False
near_ink = nd.binary_dilation((clean < 215) & roi)
doors = []
for bx in DOORS:
    sub = np.zeros_like(door_ink); sub[bx[1]:bx[3], bx[0]:bx[2]] = door_ink[bx[1]:bx[3], bx[0]:bx[2]]
    dt = nd.distance_transform_edt(sub)
    core = dt >= 1.5
    if core.sum() < 6: core = dt >= 1
    ys, xs = np.nonzero(core); P = np.c_[xs + .5, ys + .5]
    c0 = P.mean(0); u = np.linalg.svd(P - c0)[2][0]
    ys2, xs2 = np.nonzero(sub); Q = np.c_[xs2 + .5, ys2 + .5]
    perp = np.abs((Q - c0) @ np.array([-u[1], u[0]]))
    t = (Q[perp <= 2.0] - c0) @ u
    e1, e2 = c0 + u * t.min(), c0 + u * t.max()
    d1 = wall_dist[int(e1[1]), int(e1[0])]; d2 = wall_dist[int(e2[1]), int(e2[0])]
    hinge, tip = (e1, e2) if d1 <= d2 else (e2, e1)
    step = (hinge - tip) / np.hypot(*(hinge - tip))
    for _ in range(12):                              # slide the hinge out along the leaf onto the wall face
        nxt = hinge + step * 0.5
        if wall[int(nxt[1]), int(nxt[0])]: break
        hinge = nxt
    r = float(np.hypot(*(tip - hinge)))
    a_leaf = math.atan2(tip[1] - hinge[1], tip[0] - hinge[0])
    best = None
    for ax in (0, math.pi / 2, math.pi, -math.pi / 2):
        delta = (ax - a_leaf + math.pi) % (2 * math.pi) - math.pi
        if not (0.35 < abs(delta) < 2.2): continue
        angs = a_leaf + np.linspace(0.15, 0.95, 12) * delta
        hits = [near_ink[int(hinge[1] + r * math.sin(a)), int(hinge[0] + r * math.cos(a))] for a in angs]
        score = float(np.mean(hits))
        if best is None or score > best[0]: best = (score, ax, delta)
    score, ax, delta = best
    closed = hinge + r * np.array([math.cos(ax), math.sin(ax)])
    doors.append(dict(hinge=hinge, tip=tip, closed=closed, r=r, sweep=1 if delta > 0 else 0, score=score))
# room 2's door: the arc and the 0,93 / 1,05 dimensions overlap its leaf, the fit can't separate them;
# read by hand from a 10x zoom of the original: hinge on the room 2 wall, leaf to the upper left, closes upward
def set_door(i, hinge, r, closed, toward):
    """Door placed by hand: hinge on the jamb corner, leaf of length r pointing at `toward`, closing at `closed`."""
    h_ = np.array(hinge, float); v = np.array(toward, float) - h_
    doors[i] = dict(hinge=h_, tip=h_ + v / np.hypot(*v) * r, closed=np.array(closed, float), r=r,
                    sweep=doors[i]['sweep'], score=1.0)


# read on 10-18x zooms of the original (Fable review): hinge on the pier corner, leaf ≈ opening width
set_door(1, (315.5, 718.5), 27.0, (315.5, 691.5), (300.5, 695.0))       # room 2 <- oficiu
k4 = min(range(len(doors)), key=lambda i: np.hypot(*(doors[i]['hinge'] - (266.3, 1059.1))))
set_door(k4, (267.5, 1056.0), 29.0, (267.5, 1085.0), tuple(doors[k4]['tip']))   # room 4 <- hall
print('doors', len(doors), 'arc fit scores', [round(d['score'], 2) for d in doors])
print('windows', len(windows), 'lines')

# ---------------------------------------------------------------- room names (survey table "Recapitulatie")
ROOMS = {1: ('Camera', '17,80'), 2: ('Camera', '11,45'), 3: ('Camera', '10,23'), 4: ('Camera', '10,23'),
         5: ('Bucatarie', '7,85'), 6: ('Baie', '4,07'), 7: ('Baie', '2,61'), 8: ('Camara', '1,55'), 9: ('Debara', '0,46'),
         10: ('Debara', '0,59'), 11: ('Hol', '9,76'), 12: ('Oficiu', '0,98'), 13: ('Balcon', '2,64'), 14: ('Balcon', '4,90')}
# label anchor per room (screenshot px), near where the survey puts the room number; small rooms get small text
ROOM_AT = {1: (292, 784, 6), 2: (257, 655, 6), 3: (205, 1000, 6), 4: (205, 1108, 6), 5: (206, 896, 5.5), 6: (357, 640, 4),
           7: (300, 1125, 3.6), 8: (360, 873, 3.2), 9: (318, 1071, 2.2), 10: (372, 711, 2.2), 11: (298, 1003, 4.5),
           12: (338, 704, 2.4), 13: (178, 790, 3.2), 14: (119, 1057, 3.2)}

# ---------------------------------------------------------------- SVG
STYLE = {'window': ('#1565ff', 1.3), 'door': ('#e8590c', 1.3), 'doorraw': ('#e8590c', 1.2), 'rail': ('#555555', 1.0), 'partition': ('#666666', 1.0)}
NAMES = {'doorraw': 'usa_debara', 'window': 'geamuri', 'door': 'usi', 'rail': 'balustrade', 'partition': 'alte'}
x1, y1, x2, y2 = ROI
VB = f'{x1} {y1} {x2 - x1} {y2 - y1}'


def svg(dots=False, only_walls_black=False, lines_black=False):
    d = ' '.join('M' + ' '.join(f'{x},{y}' for x, y in l) + 'Z' for l in loops)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VB}" width="{(x2 - x1) * 3}" height="{(y2 - y1) * 3}">',
         '<!-- 1 unit = 1 px of the survey screenshot; 34.6 units = 1 m -->',
         '<defs><pattern id="hasura" width="3" height="3" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<rect width="3" height="3" fill="#9a9a9a"/><line x1="0" y1="0" x2="0" y2="3" stroke="#5a5a5a" stroke-width="1.2"/></pattern></defs>',
         f'<rect x="{x1}" y="{y1}" width="{x2 - x1}" height="{y2 - y1}" fill="#fff"/>']
    if only_walls_black:
        o.append(f'<path id="pereti" d="{d}" fill="#000" fill-rule="evenodd" shape-rendering="crispEdges"/>')
    else:
        o.append(f'<path id="pereti" d="{d}" fill="url(#hasura)" fill-rule="evenodd" stroke="#000" stroke-width="0.6" stroke-linejoin="miter"/>')
    for cls in ('rail', 'partition', 'doorraw'):
        col, w = STYLE[cls]
        if lines_black: col = '#000'
        if only_walls_black and not lines_black: continue
        o.append(f'<g id="{NAMES[cls]}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round">')
        for c, pts in lines:
            if c == cls:
                o.append('<polyline points="' + ' '.join(f'{x:g},{y:g}' for x, y in pts) + '"/>')
        o.append('</g>')
    if not (only_walls_black and not lines_black):
        wc = '#000' if lines_black else STYLE['window'][0]
        dc = '#000' if lines_black else STYLE['door'][0]
        o.append(f'<g id="geamuri" fill="none" stroke="{wc}" stroke-width="1.1" stroke-linecap="butt">')
        for (ax_, ay), (bx_, by) in windows:
            o.append(f'<line x1="{ax_:g}" y1="{ay:g}" x2="{bx_:g}" y2="{by:g}"/>')
        o.append('</g>')
        o.append(f'<g id="usi" fill="none" stroke="{dc}" stroke-linecap="round">')
        for d_ in doors:
            h_, t_, c_ = d_['hinge'], d_['tip'], d_['closed']
            o.append(f'<line x1="{h_[0]:.2f}" y1="{h_[1]:.2f}" x2="{t_[0]:.2f}" y2="{t_[1]:.2f}" stroke-width="2.2"/>')
            o.append(f'<path d="M{t_[0]:.2f},{t_[1]:.2f} A{d_["r"]:.2f},{d_["r"]:.2f} 0 0 {d_["sweep"]} {c_[0]:.2f},{c_[1]:.2f}" stroke-width="0.9"/>')
        o.append('</g>')
    if not only_walls_black:
        o.append('<g id="camere" font-family="Helvetica, Arial, sans-serif" fill="#333" text-anchor="middle">')
        for k, (nm, ar) in ROOMS.items():
            x_, y_, fs = ROOM_AT[k]
            o.append(f'<text x="{x_}" y="{y_}" font-size="{fs}"><tspan font-weight="bold">{k}. {nm}</tspan>'
                     f'<tspan x="{x_}" dy="{fs * 1.15:.2f}">{ar} m²</tspan></text>')
        o.append('</g>')
    if dots:
        o.append('<g id="varfuri" fill="#e00000">')
        for l in loops:
            for x, y in l: o.append(f'<circle cx="{x}" cy="{y}" r="0.9"/>')
        o.append('</g>')
    o.append('</svg>')
    return '\n'.join(o) + '\n'


open('plan.svg', 'w').write(svg())
open('plan_varfuri.svg', 'w').write(svg(dots=True))
open('plan_walls_black.svg', 'w').write(svg(only_walls_black=True))
open('plan_lines_black.svg', 'w').write(svg(only_walls_black=True, lines_black=True))

# ---------------------------------------------------------------- DXF (metres, y up)
def m(x, y):
    return ((x - x1) / PX_PER_M, (y2 - y) / PX_PER_M)


doc = ezdxf.new('R2010', setup=True)
doc.units = ezdxf.units.M
msp = doc.modelspace()
for name, color in (('PERETI', 7), ('FERESTRE', 5), ('USI', 30), ('BALUSTRADE', 8), ('ALTE', 8), ('COTE', 1), ('CAMERE', 2)):
    doc.layers.add(name, color=color)
for l in loops:
    msp.add_lwpolyline([m(x, y) for x, y in l], close=True, dxfattribs={'layer': 'PERETI'})
hatch = msp.add_hatch(color=8, dxfattribs={'layer': 'PERETI'})
hatch.set_pattern_fill('ANSI31', scale=0.02)
for l in loops:
    hatch.paths.add_polyline_path([m(x, y) for x, y in l], is_closed=True)
LAYER = {'doorraw': 'USI', 'window': 'FERESTRE', 'door': 'USI', 'rail': 'BALUSTRADE', 'partition': 'ALTE'}
for cls, pts in lines:
    msp.add_lwpolyline([m(x, y) for x, y in pts], dxfattribs={'layer': LAYER[cls]})
for a_, b_ in windows:
    msp.add_line(m(*a_), m(*b_), dxfattribs={'layer': 'FERESTRE'})
for d_ in doors:
    h_, t_, c_ = m(*d_['hinge']), m(*d_['tip']), m(*d_['closed'])
    msp.add_line(h_, t_, dxfattribs={'layer': 'USI', 'lineweight': 35})
    a1 = math.degrees(math.atan2(t_[1] - h_[1], t_[0] - h_[0])); a2 = math.degrees(math.atan2(c_[1] - h_[1], c_[0] - h_[0]))
    if (a2 - a1) % 360 > 180: a1, a2 = a2, a1
    msp.add_arc(h_, d_['r'] / PX_PER_M, a1, a2, dxfattribs={'layer': 'USI'})

# room dimensions of the survey: drawn on the measured inner faces, labelled with the surveyed value
DIMS = [('3,34', 'h', 615, 260), ('3,55', 'v', 260, 650), ('1,71', 'h', 603, 360), ('2,38', 'v', 385, 640),
        ('5,22', 'h', 740, 300), ('3,41', 'v', 380, 780), ('1,50', 'h', 888, 360), ('1,03', 'v', 385, 870),
        ('2,40', 'v', 180, 900), ('3,35', 'h', 930, 200), ('3,52', 'h', 960, 200), ('2,95', 'v', 175, 1000),
        ('2,96', 'v', 175, 1110), ('3,52', 'h', 1150, 200)]


def span(o, c, at):
    if o == 'h':
        row = wall[c]; a = at
        while not row[a]: a -= 1
        b = at
        while not row[b]: b += 1
        return a + 1, b
    col = wall[:, c]; a = at
    while not col[a]: a -= 1
    b = at
    while not col[b]: b += 1
    return a + 1, b


dim_report = []
for txt, o, c, at in DIMS:
    a, b = span(o, c, at)
    if o == 'h':
        p1, p2, base = m(a, c), m(b, c), m(a, c)
        dim = msp.add_linear_dim(base=(p1[0], p1[1]), p1=p1, p2=p2, angle=0, text=txt, dimstyle='EZDXF',
                                 override={'dimtxt': 0.12, 'dimasz': 0.08}, dxfattribs={'layer': 'COTE'})
    else:
        p1, p2 = m(c, b), m(c, a)
        dim = msp.add_linear_dim(base=(p1[0], p1[1]), p1=p1, p2=p2, angle=90, text=txt, dimstyle='EZDXF',
                                 override={'dimtxt': 0.12, 'dimasz': 0.08}, dxfattribs={'layer': 'COTE'})
    dim.render()
    dim_report.append(f'{txt}: masurat {(b - a) / PX_PER_M:.2f} m')
for k, (nm, ar) in ROOMS.items():
    x_, y_, fs = ROOM_AT[k]
    h_ = fs / PX_PER_M * 0.8
    msp.add_text(f'{k}. {nm}', height=h_, dxfattribs={'layer': 'CAMERE'}).set_placement(m(x_, y_), align=TextEntityAlignment.BOTTOM_CENTER)
    msp.add_text(f'{ar} m2', height=h_ * 0.85, dxfattribs={'layer': 'CAMERE'}).set_placement(m(x_, y_ + fs * 1.15), align=TextEntityAlignment.BOTTOM_CENTER)
doc.saveas('plan.dxf')
print('walls', len(loops), 'loops,', sum(len(l) for l in loops), 'vertices;',
      'lines', {k: sum(1 for c, _ in lines if c == k) for k in STYLE})
print('; '.join(dim_report))
