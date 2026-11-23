"""Trace target_mask.png into orthogonal polygons, simplify pixel noise, write walls.svg."""
import sys
import numpy as np
from PIL import Image

MAXJOG = 3      # max bump/notch depth to flatten (px)
MAXLEN = 8      # max bump/notch width to flatten (px)


def trace(mask):
    """Directed boundary edges with the wall on the left; chained into closed loops."""
    p = np.pad(mask, 1)
    nxt = {}
    ys, xs = np.nonzero(p[1:-1, 1:-1])
    for y, x in zip(ys, xs):
        Y, X = y + 1, x + 1
        # pixel occupies [x,x+1]x[y,y+1]; walk clockwise-on-screen so wall is on the right (y down)
        if not p[Y - 1, X]: nxt.setdefault((x, y), []).append((x + 1, y))          # top edge  ->
        if not p[Y, X + 1]: nxt.setdefault((x + 1, y), []).append((x + 1, y + 1))  # right edge v
        if not p[Y + 1, X]: nxt.setdefault((x + 1, y + 1), []).append((x, y + 1))  # bottom <-
        if not p[Y, X - 1]: nxt.setdefault((x, y + 1), []).append((x, y))          # left ^
    loops = []
    while nxt:
        start = next(iter(nxt))
        loop, cur, prev_dir = [start], start, None
        while True:
            outs = nxt[cur]
            if len(outs) == 1:
                n = outs[0]
            else:  # saddle point: prefer turning right (keeps diagonal-touching pixels separate)
                def turn(o):
                    d = (o[0] - cur[0], o[1] - cur[1])
                    return 0 if prev_dir is None else (prev_dir[0] * d[1] - prev_dir[1] * d[0])
                n = max(outs, key=turn)
            outs.remove(n)
            if not outs: del nxt[cur]
            prev_dir = (n[0] - cur[0], n[1] - cur[1])
            cur = n
            if cur == start and (start not in nxt):
                break
            if cur == start:
                break
            loop.append(cur)
        loops.append(loop)
    return loops


def merge(pts):
    """Drop collinear and duplicate vertices of a closed orthogonal loop."""
    changed = True
    while changed and len(pts) > 4:
        changed = False
        out = []
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if b == a: changed = True; continue
            if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
                changed = True; continue
            out.append(b)
        pts = out
    return pts


def simplify(pts):
    """Flatten small bumps/notches (U shapes) and 1px stair steps (Z shapes)."""
    for _ in range(200):
        pts = merge(pts)
        n = len(pts)
        if n <= 4: return pts
        best = None
        for i in range(n):
            p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            # edges: e0=p0->p1, e1=p1->p2 (candidate), e2=p2->p3
            e0 = (p1[0] - p0[0], p1[1] - p0[1]); e1 = (p2[0] - p1[0], p2[1] - p1[1]); e2 = (p3[0] - p2[0], p3[1] - p2[1])
            l0, l1, l2 = abs(sum(e0)), abs(sum(e1)), abs(sum(e2))
            s0 = (np.sign(e0[0]), np.sign(e0[1])); s2 = (np.sign(e2[0]), np.sign(e2[1]))
            if s0 == (-s2[0], -s2[1]):           # U: bump or notch of depth min(l0,l2), width l1
                h = min(l0, l2)
                if h <= MAXJOG and l1 <= MAXLEN:
                    cost = h * l1
                    if best is None or cost < best[0]: best = (cost, 'U', i, h, s0)
            elif s0 == s2 and l1 <= MAXJOG:      # Z: a step of l1 between two parallel arms
                short = min(l0, l2)
                if short <= MAXLEN or (l1 == 1 and short <= 60):   # 1px steps on long faces are JPEG noise (1px = 3 cm)
                    cost = short * l1
                    if best is None or cost < best[0]: best = (cost, 'Z', i, l0 <= l2)
        if best is None: return pts
        if best[1] == 'U':
            _, _, i, h, s0 = best
            # move edge p1->p2 back against e0's direction by h
            dx, dy = -s0[0] * h, -s0[1] * h
            j = (i + 1) % n
            pts[i] = (pts[i][0] + dx, pts[i][1] + dy); pts[j] = (pts[j][0] + dx, pts[j][1] + dy)
        else:
            _, _, i, first_short = best
            j = (i + 1) % n
            p1, p2 = pts[i], pts[j]
            step = (p2[0] - p1[0], p2[1] - p1[1])
            if first_short:   # slide arm e0 (p0->p1) onto the line of e2: move p0 and p1 by step
                k = (i - 1) % n
                pts[k] = (pts[k][0] + step[0], pts[k][1] + step[1]); pts[i] = p2
            else:             # slide arm e2 back onto e0's line
                k = (i + 2) % n
                pts[k] = (pts[k][0] - step[0], pts[k][1] - step[1]); pts[j] = p1
    return merge(pts)




def wall_loops(mask):
    return [l for l in (simplify(merge(l)) for l in trace(mask)) if len(l) >= 4]


if __name__ == '__main__':
    MAXJOG = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    MAXLEN = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    m = np.asarray(Image.open(sys.argv[3] if len(sys.argv) > 3 else 'target_mask.png')) > 127
    H, W = m.shape
    loops = [simplify(merge(l)) for l in trace(m)]
    loops = [l for l in loops if len(l) >= 4]
    d = ' '.join('M' + ' '.join(f'{x},{y}' for x, y in l) + 'Z' for l in loops)
    nv = sum(len(l) for l in loops)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'shape-rendering="crispEdges">\n'
           f'<path fill="#000" fill-rule="evenodd" d="{d}"/>\n</svg>\n')
    open('walls.svg', 'w').write(svg)
    print('loops', len(loops), 'vertices', nv)
