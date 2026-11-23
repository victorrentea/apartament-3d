"""Zoom pairs original | vector render for Victor's marked spots -> spots.png"""
import sys
from PIL import Image, ImageDraw
SPOTS = {1:(185,643,220,672),2:(348,596,396,620),3:(317,594,348,629),4:(307,664,341,699),5:(374,670,389,691),6:(381,866,402,901),
         7:(313,843,343,860),8:(317,843,340,873),9:(121,942,170,981),10:(253,1039,282,1073),11:(308,1075,349,1089),12:(133,1110,150,1122),13:(147,851,168,929)}
o = Image.open('original.jpg').convert('RGB'); p = Image.open(sys.argv[1] if len(sys.argv) > 1 else 'plan.png').convert('RGB')
X0, Y0, S = 20, 585, p.width / 390
Z = 7; P = 5
tiles = []
for k, (a, b, c, d) in SPOTS.items():
    a, b, c, d = a - P, b - P, c + P, d + P
    w, h = (c - a) * Z, (d - b) * Z
    t = Image.new('RGB', (2 * w + 12, h + 18), 'white')
    t.paste(o.crop((a, b, c, d)).resize((w, h), Image.NEAREST), (0, 18))
    t.paste(p.crop((int((a - X0) * S), int((b - Y0) * S), int((c - X0) * S), int((d - Y0) * S))).resize((w, h), Image.LANCZOS), (w + 12, 18))
    ImageDraw.Draw(t).text((2, 2), f'#{k} ({a},{b})-({c},{d})', fill='red'); tiles.append(t)
# pack rows of max width 2400
rows, row, rw = [], [], 0
for t in tiles:
    if rw + t.width > 2400 and row: rows.append(row); row, rw = [], 0
    row.append(t); rw += t.width + 10
rows.append(row)
Wd = max(sum(t.width + 10 for t in r) for r in rows); Ht = sum(max(t.height for t in r) + 10 for r in rows)
out = Image.new('RGB', (Wd, Ht), (230, 230, 230)); y = 0
for r in rows:
    x = 0
    for t in r: out.paste(t, (x, y)); x += t.width + 10
    y += max(t.height for t in r) + 10
out.save('spots.png'); print(out.size)
