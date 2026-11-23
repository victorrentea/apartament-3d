"""Room areas measured on the vector plan vs the survey's table (Recapitulatie).

Each room = the free floor reachable from its label point, with every opening closed:
walls (filled), doors closed (hinge -> closed position), window lines, rails, partitions.
Rasterised at 4x, 34.6 px = 1 m.
"""
import re
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

PX_PER_M, K = 34.6, 4
X1, Y1, X2, Y2 = 20, 585, 410, 1175
TABLE = {1: ('Camera', 17.80), 2: ('Camera', 11.45), 3: ('Camera', 10.23), 4: ('Camera', 10.23), 5: ('Bucatarie', 7.85),
         6: ('Baie', 4.07), 7: ('Baie', 2.61), 8: ('Camara', 1.55), 9: ('Debara', 0.46), 10: ('Debara', 0.59),
         11: ('Hol', 9.76), 12: ('Oficiu', 0.98), 13: ('Balcon', 2.64), 14: ('Balcon', 4.90)}
# where each room's circled number sits on the original (screenshot px)
LABEL = {1: (292, 784), 2: (257, 651), 3: (202, 1000), 4: (202, 1104), 5: (206, 894), 6: (357, 638), 7: (294, 1116),
         8: (361, 873), 9: (319, 1069), 10: (368, 712), 11: (298, 1003), 12: (335, 706), 13: (181, 812), 14: (121, 1057)}

svg = open('plan.svg').read()
img = Image.new('L', ((X2 - X1) * K, (Y2 - Y1) * K), 0)
dr = ImageDraw.Draw(img)
P = lambda x, y: ((float(x) - X1) * K, (float(y) - Y1) * K)

walls = re.search(r'id="pereti" d="([^"]+)"', svg).group(1)
for seg in walls.split('M')[1:]:
    pts = [P(*p.split(',')) for p in seg.strip(' Z').split()]
    dr.polygon(pts, fill=255)
def stroke(pts, ext=1.5):
    """Draw a barrier polyline, its ends pushed 1.5 px further so it really meets the wall it ends on."""
    pts = [np.array(p, float) for p in pts]
    if len(pts) >= 2:
        for end, nb in ((0, 1), (-1, -2)):
            d = pts[end] - pts[nb]; L = np.hypot(*d)
            if L > 0: pts[end] = pts[end] + d / L * ext
    dr.line([P(*p) for p in pts], fill=255, width=K + 1)


for m in re.finditer(r'<polyline points="([^"]+)"', svg):
    stroke([tuple(map(float, p.split(','))) for p in m.group(1).split()])
for m in re.finditer(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)"', svg):
    stroke([(float(m[1]), float(m[2])), (float(m[3]), float(m[4]))])
# doors: close them (hinge -> closed point, pushed 4 px into the jambs: some hinges float ~3 px off the wall); the hinge is the x1,y1 of the leaf line right before each arc
leafs = re.findall(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" stroke-width="2.2"/>\s*<path d="M[\d.,]+ A[\d.,]+ 0 0 \d ([\d.]+),([\d.]+)"', svg)
for hx, hy, _, _, cx, cy in leafs:                   # extended 1.5 px past both ends so no hairline gap leaks
    a_, b_ = np.array([float(hx), float(hy)]), np.array([float(cx), float(cy)])
    u = (b_ - a_) / np.hypot(*(b_ - a_))
    dr.line([P(*(a_ - 4 * u)), P(*(b_ + 4 * u))], fill=255, width=K + 1)

barrier = np.asarray(img) > 0
free = ~barrier
lab, n = nd.label(free)
print(f'{"nr":>2} {"destinatie":10} {"tabel":>6} {"masurat":>8} {"dif":>6}')
tot_t = tot_m = 0
for k, (x, y) in LABEL.items():
    yy, xx = int((y - Y1) * K), int((x - X1) * K)
    l = lab[yy, xx]
    if l == 0:
        print(k, 'label point falls on a barrier'); continue
    area = (lab == l).sum() / K ** 2 / PX_PER_M ** 2
    name, t = TABLE[k]
    tot_t += t; tot_m += area
    flag = '' if abs(area - t) / t < 0.08 else '  <-- '
    print(f'{k:>2} {name:10} {t:6.2f} {area:8.2f} {100 * (area - t) / t:+5.1f}%{flag}')
print(f'   {"total":10} {tot_t:6.2f} {tot_m:8.2f} {100 * (tot_m - tot_t) / tot_t:+5.1f}%')

if __name__ == '__main__' and __import__('os').environ.get('DEBUG'):
    rgb = np.zeros(barrier.shape + (3,), np.uint8); rgb[barrier] = (0, 0, 0); rgb[free] = (255, 255, 255)
    for k in (13, 4):
        x, y = LABEL[k]; l = lab[int((y - Y1) * K), int((x - X1) * K)]
        rgb[lab == l] = (255, 180, 180) if k == 3 else (180, 255, 180)
    Image.fromarray(rgb).resize(((X2 - X1) * 2, (Y2 - Y1) * 2)).save('areas_debug.png')
