"""Per-room review images: original | vector | overlay on a 10 cm / 1 m grid -> rooms/room_<n>.png"""
import os, re, subprocess
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

X1, Y1, X2, Y2 = 20, 585, 410, 1175
Z = 6
PX_PER_M = 34.6
SCR = '/private/tmp/claude-501/-Users-victorrentea-workspace/2bc7a939-bce2-54fc-9eca-276513fb09ae/scratchpad/'
ROOMS = {1: (190, 714, 400, 862), 2: (186, 585, 332, 737), 3: (122, 938, 277, 1062), 4: (122, 1043, 277, 1172),
         5: (122, 843, 277, 952), 6: (312, 585, 400, 697), 7: (268, 1078, 347, 1172), 8: (298, 838, 400, 902),
         9: (288, 1033, 347, 1097), 10: (333, 688, 400, 737), 11: (248, 838, 347, 1112), 12: (288, 653, 362, 737),
         13: (148, 713, 217, 862), 14: (88, 928, 152, 1172)}
os.makedirs('rooms', exist_ok=True)


def render(svg, out):
    s = open(svg).read()
    s = re.sub(r'width="\d+" height="\d+"', f'width="{(X2 - X1) * Z}" height="{(Y2 - Y1) * Z}"', s, count=1)
    open(SCR + 'r.svg', 'w').write(s)
    subprocess.run(['rsvg-convert', '-b', 'white', '-o', out, SCR + 'r.svg'], check=True)
    return Image.open(out).convert('RGB')


vec = render('plan.svg', SCR + 'vec6.png')
walls = np.asarray(render('plan_walls_black.svg', SCR + 'w6.png').convert('L')) < 128
outline = walls & ~nd.binary_erosion(walls, np.ones((3, 3)))
orig = Image.open('original.jpg').convert('RGB')

for k, (a, b, c, d) in ROOMS.items():
    w, h = (c - a) * Z, (d - b) * Z
    o = orig.crop((a, b, c, d)).resize((w, h), Image.NEAREST)
    box = ((a - X1) * Z, (b - Y1) * Z, (c - X1) * Z, (d - Y1) * Z)
    v = vec.crop(box)
    ol = outline[box[1]:box[3], box[0]:box[2]]
    base = np.asarray(o).astype(float)
    ov = (base * 0.55 + 255 * 0.45).astype(np.uint8)
    img = Image.fromarray(ov); dr = ImageDraw.Draw(img)
    # 10 cm grid (light) and 1 m grid (darker), anchored at the drawing origin (X1, Y1)
    step = PX_PER_M / 10 * Z
    for i in range(0, 400):
        gx = (X1 - a) * Z + i * step
        if 0 <= gx < w: dr.line([(gx, 0), (gx, h)], fill=(120, 200, 255) if i % 10 else (0, 110, 220), width=1 if i % 10 else 2)
        gy = (Y1 - b) * Z + i * step
        if 0 <= gy < h: dr.line([(0, gy), (w, gy)], fill=(120, 200, 255) if i % 10 else (0, 110, 220), width=1 if i % 10 else 2)
    arr = np.asarray(img).copy(); arr[ol] = (230, 0, 0)
    img = Image.fromarray(arr)
    out = Image.new('RGB', (3 * w + 40, h + 40), 'white')
    for j, im in enumerate((o, v, img)): out.paste(im, (j * (w + 20), 40))
    t = ImageDraw.Draw(out)
    t.text((4, 4), f'Room {k}: original (left) | vector (middle) | overlay: red = vector wall outline over the original, grid 10 cm / 1 m (blue). '
                   f'Crop of original px x {a}-{c}, y {b}-{d}; zoom {Z}x', fill='black')
    out.save(f'rooms/room_{k}.png')
print('ok', len(ROOMS))
