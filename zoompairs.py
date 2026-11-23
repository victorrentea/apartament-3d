import sys
from PIL import Image, ImageDraw
regs = {1:(335,662,410,705),2:(370,568,410,612),3:(362,827,410,905),4:(250,830,285,885),5:(254,1145,300,1180),6:(124,932,153,984),7:(190,715,217,746),8:(150,823,208,857)}
o = Image.open('original.jpg').convert('RGB'); c = Image.open(sys.argv[1] if len(sys.argv) > 1 else 'clean.png').convert('RGB')
rows = []
for k, b in regs.items():
    w, h = b[2]-b[0], b[3]-b[1]; s = 6
    im = Image.new('RGB', (2*w*s+20, h*s+16), 'white')
    im.paste(o.crop(b).resize((w*s, h*s), Image.NEAREST), (0, 16)); im.paste(c.crop(b).resize((w*s, h*s), Image.NEAREST), (w*s+20, 16))
    ImageDraw.Draw(im).text((2, 2), f'#{k} {b}', fill='red'); rows.append(im)
W = max(r.width for r in rows)
# two columns
cols = [rows[:4], rows[4:]]
colw = [max(r.width for r in col) for col in cols]; colh = [sum(r.height + 8 for r in col) for col in cols]
out = Image.new('RGB', (sum(colw) + 30, max(colh)), (240, 240, 240))
x = 0
for col, cw in zip(cols, colw):
    y = 0
    for r in col: out.paste(r, (x, y)); y += r.height + 8
    x += cw + 30
out.save('zooms.png'); print(out.size)
