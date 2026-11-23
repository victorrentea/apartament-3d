"""Render walls.svg with rsvg-convert, compare against target_mask.png, write diff images."""
import subprocess, sys
import numpy as np
from PIL import Image

svg = sys.argv[1] if len(sys.argv) > 1 else 'walls.svg'
subprocess.run(['rsvg-convert', '-b', 'white', '-o', 'render.png', svg], check=True)
r = np.asarray(Image.open('render.png').convert('L')) < 128
t = np.asarray(Image.open('target_mask.png')) > 127
assert r.shape == t.shape, (r.shape, t.shape)
x = r ^ t
tot = t.size
print(f'diff px {x.sum()}  = {100 * x.sum() / tot:.4f}% of image  ({100 * x.sum() / t.sum():.3f}% of wall area)'
      f'  extra {(r & ~t).sum()}  missing {(t & ~r).sum()}')
d = np.full(t.shape + (3,), 255, np.uint8)
d[t & r] = (170, 170, 170); d[r & ~t] = (255, 0, 0); d[t & ~r] = (0, 120, 255)
Image.fromarray(d[580:1180, 85:410]).resize((975, 1800), Image.NEAREST).save('diff3x.png')
