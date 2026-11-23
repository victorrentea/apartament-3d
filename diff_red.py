"""Pixel diff of the vector plan against the original drawing (blue dimensions removed = clean.png).

walls : vector wall polygons vs the drawing's wall ink, exact pixels
lines : vector doors/windows/rails vs the drawing's thin ink, with 1 px tolerance (a 1 px line can't be
        placed more exactly than that)
Output: diff_rosu.png (original | vector | differences circled in red) and the numbers.
"""
import re, subprocess
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

X1, Y1, X2, Y2 = 20, 585, 410, 1175
W, H = X2 - X1, Y2 - Y1
SCR = '/private/tmp/claude-501/-Users-victorrentea-workspace/2bc7a939-bce2-54fc-9eca-276513fb09ae/scratchpad/'


def render(svg_path, out):
    s = open(svg_path).read()
    s = re.sub(r'width="\d+" height="\d+"', f'width="{W}" height="{H}"', s, count=1)
    open(SCR + 'tmp.svg', 'w').write(s)
    subprocess.run(['rsvg-convert', '-b', 'white', '-o', out, SCR + 'tmp.svg'], check=True)
    return np.asarray(Image.open(out).convert('L'))


vw = render('plan_walls_black.svg', SCR + 'vw.png') < 128                 # vector walls
vall = render('plan_lines_black.svg', SCR + 'vall.png') < 160             # vector walls + lines
vl = vall & ~vw

clean = np.asarray(Image.open('clean.png').convert('L')).astype(int)[Y1:Y2, X1:X2]
dw = np.asarray(Image.open('wall_mask_clean.png'))[Y1:Y2, X1:X2] > 127
edge = dw & ~nd.binary_erosion(dw)
dw &= ~(edge & (clean > 145))                                             # same fringe rule as the plan
dl = (clean < 170) & ~nd.binary_dilation(dw, np.ones((3, 3)))             # thin ink of the drawing

wall_diff = vw ^ dw
tol = np.ones((3, 3), bool)
line_extra = vl & ~nd.binary_dilation(dl, tol) & ~nd.binary_dilation(dw, tol)
line_miss = dl & ~nd.binary_dilation(vl, tol) & ~nd.binary_dilation(vw, tol)
diff = wall_diff | line_extra | line_miss

tot = W * H
print(f'walls: {wall_diff.sum()} px differ = {100 * wall_diff.sum() / tot:.3f}% of the drawing area, '
      f'{100 * wall_diff.sum() / dw.sum():.2f}% of the wall area ({dw.sum()} px)')
print(f'lines (1px tolerance): {line_extra.sum()} px drawn where the original has none, '
      f'{line_miss.sum()} px of the original not drawn')

# circle clusters
S = 3
orig = Image.open('original.jpg').convert('RGB').crop((X1, Y1, X2, Y2)).resize((W * S, H * S), Image.LANCZOS)
vec = Image.open('plan.png').convert('RGB').resize((W * S, H * S), Image.LANCZOS)
base = np.asarray(orig).astype(float) * 0.35 + 255 * 0.65
ov = Image.fromarray(base.astype(np.uint8))
vimg = np.asarray(vec).astype(float)
mask_v = np.kron(vall, np.ones((S, S), bool))
arr = np.asarray(ov).copy(); arr[mask_v] = (vimg[mask_v] * 0.8 + base[mask_v] * 0.2)
d_big = np.kron(diff, np.ones((S, S), bool)); arr[d_big] = (255, 0, 0)
ov = Image.fromarray(arr.astype(np.uint8)); dr = ImageDraw.Draw(ov)
lab, n = nd.label(nd.binary_dilation(diff, np.ones((5, 5))))
k = 0
for i, sl in enumerate(nd.find_objects(lab), 1):
    if (diff[sl] & (lab[sl] == i)).sum() < 3: continue
    k += 1
    cy, cx = (sl[0].start + sl[0].stop) / 2 * S, (sl[1].start + sl[1].stop) / 2 * S
    r = max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) / 2 * S + 8
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 0, 0), width=3)
print('red circles:', k)
out = Image.new('RGB', (W * S * 3 + 40, H * S + 60), 'white')
for j, im in enumerate((orig, vec, ov)):
    out.paste(im, (j * (W * S + 20), 60))
d = ImageDraw.Draw(out)
d.text((10, 20), 'Original', fill='black')
d.text((W * S + 30, 20), 'Vectorizat', fill='black')
d.text((2 * W * S + 50, 20), f'Diferente (rosu): pereti {wall_diff.sum()} px, linii +{line_extra.sum()}/-{line_miss.sum()} px', fill='red')
out.save('diff_rosu.png')
