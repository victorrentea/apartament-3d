"""Step 1: the original drawing without the blue dimensions and the room-number circles -> clean.png

1. find blue ink (relative to darkness: JPEG tints black lines / grey hatch next to blue, those stay)
2. decide wall vs paper for every pixel from the NON-blue ink; a blue pixel is wall/line only if the
   ink continues on both sides of it along a row or a column (a dimension crossing a wall or a line)
3. repaint: blue on wall -> hatch borrowed from the nearest real wall pixel; blue on line -> line;
   blue on paper -> white. Output is greyscale (the drawing has no other colour).
"""
import numpy as np
from PIL import Image
from scipy import ndimage as nd

a = np.asarray(Image.open('original.jpg').convert('RGB')).astype(float)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
gray = a.mean(2)
H, W = gray.shape
roi = np.zeros((H, W), bool); roi[585:1175, 20:410] = True

bness = b - (r + g) / 2
rel = bness / (256 - gray)
core = (bness > 12) & (rel > 0.27) & roi                       # surely blue ink
loose = ((bness > 6) & (rel > 0.12) & roi) | core                # blue ink OR something tinted by it
loose |= nd.binary_dilation(core) & (bness > 3) & (gray > 170) & roi
blue = core

# --- wall classification from non-blue pixels -------------------------------------------------------
dark = (gray < 200) & ~blue
nb = nd.uniform_filter((~blue).astype(float), 5)
D = nd.uniform_filter(dark.astype(float), 5) / np.maximum(nb, 1e-6)
wall0 = (D > 0.45) & ~blue & roi
wall0 = nd.binary_opening(wall0, np.ones((3, 3)))            # walls are >= 5px thick; lines are not
line0 = (gray < 160) & ~blue & ~wall0 & roi                 # thin black/grey lines (doors, windows, rails)


def first_clear(y, x, dy, dx):
    while 0 <= y < H and 0 <= x < W and blue[y, x]:
        y += dy; x += dx
    return (y, x) if 0 <= y < H and 0 <= x < W else None


out = gray.copy()
wallmask = wall0.copy()
for y, x in zip(*np.nonzero(blue)):
    val = 255.0
    for dy, dx in ((0, 1), (1, 0)):
        p, q = first_clear(y, x, dy, dx), first_clear(y, x, -dy, -dx)
        if not (p and q): continue
        span = abs(p[0] - q[0]) + abs(p[1] - q[1])
        if span <= 16 and wall0[p] and wall0[q]:
            wallmask[y, x] = True; val = None; break
        if span <= 7 and (line0[p] or wall0[p]) and (line0[q] or wall0[q]):
            near = p if abs(p[0] - y) + abs(p[1] - x) <= abs(q[0] - y) + abs(q[1] - x) else q
            val = gray[near]; break
    if val is not None:
        out[y, x] = val

# paper: anything bluish that is not wall and not a real dark line goes white
# a tinted dark pixel is a real line (rail, window frame) if the same line continues, untinted,
# along its row or column; a blue dimension line is blue all along
U = (gray < 170) & (bness < 12) & ~nd.binary_dilation(wall0, np.ones((5, 5))) & roi
cnt_col = nd.uniform_filter1d(U.astype(float), 25, axis=0) * 25
cnt_row = nd.uniform_filter1d(U.astype(float), 25, axis=1) * 25
real_line = loose & ~core & (gray < 190) & ((cnt_col >= 4) | (cnt_row >= 4))
paper_blue = loose & ~blue & ~nd.binary_dilation(wallmask) & ~real_line
out[paper_blue] = 255

# hatch texture for blue pixels that are wall: copy the nearest real (non-blue) wall pixel
fillw = blue & wallmask
_, (iy, ix) = nd.distance_transform_edt(~(wall0), return_indices=True)
out[fillw] = gray[iy, ix][fillw]

# --- room-number circles: small, roughly square, isolated blobs away from walls ------------------------
near_wall = nd.binary_dilation(np.asarray(Image.open('target_mask.png')) > 127, np.ones((3, 3)))   # robust wall mask (circles are not in it)
ink = (out < 200) & roi & ~near_wall
lab, n = nd.label(ink, np.ones((3, 3)))
removed = 0
for i, sl in enumerate(nd.find_objects(lab), 1):
    h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
    if 7 <= h <= 15 and 7 <= w <= 15 and abs(h - w) <= 3:
        box = (slice(sl[0].start - 1, sl[0].stop + 1), slice(sl[1].start - 1, sl[1].stop + 1))
        out[box][~near_wall[box]] = 255
        removed += 1
# the "10" label sits on the wall step of closet 10, so it is not isolated: erase it by hand
out[704:719, 358:371] = 255
# the "13" label touches the balcony 13 rail: erase it by hand (between the two rail lines)
out[804:820, 173:189] = 255

# leftover specks (decimal points, digit fragments) and faint ghosts on paper
spk = (out < 225) & roi & ~near_wall
lab, n = nd.label(spk, np.ones((3, 3)))
sz = nd.sum(spk, lab, range(1, n + 1))
out[np.isin(lab, np.nonzero(sz <= 8)[0] + 1)] = 255
out[(out > 215) & ~near_wall & roi] = 255
print('circles removed', removed)

Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save('clean.png')
Image.fromarray((wallmask * 255).astype(np.uint8)).save('clean_wallmask.png')
