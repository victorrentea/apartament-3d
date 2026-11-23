"""Extract the hatched-wall mask from the original screenshot -> target_mask.png."""
import numpy as np, sys
from PIL import Image
from scipy import ndimage as nd

SRC = sys.argv[3] if len(sys.argv) > 3 else 'original.jpg'
OUT = sys.argv[4] if len(sys.argv) > 4 else 'target_mask.png'
a = np.asarray(Image.open(SRC).convert('RGB')).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
gray = a.mean(2)
blue = (b - (r + g) / 2) > 25
nonwhite = (gray < 215) & ~blue
dark = (gray < 200) & ~blue
roi = np.zeros_like(dark); roi[585:1175, 90:405] = True
dark &= roi; nonwhite &= roi

K = int(sys.argv[1]) if len(sys.argv) > 1 else 4
OP = int(sys.argv[2]) if len(sys.argv) > 2 else 5
core = (gray < 95) & ~blue & roi   # hatch has many near-black pixels; rails/window frames are mid-grey lines
dens = nd.uniform_filter(core.astype(float), size=5)
coarse = dens > 0.2
coarse = nd.binary_closing(coarse, np.ones((3, 3)))
coarse = nd.binary_opening(coarse, np.ones((K, K)))   # kills diagonal door leaves & thin lines
lab, n = nd.label(coarse); sizes = nd.sum(coarse, lab, range(1, n + 1))
coarse = np.isin(lab, np.nonzero(sizes >= 60)[0] + 1)

# refine edges on the real ink: within 2px of the coarse wall, keep non-white ink, close the hatch gaps
near = nd.binary_dilation(coarse, np.ones((5, 5)))


def refine(ink):
    f = nd.binary_closing(ink & near, np.ones((3, 3))) & near
    f = nd.binary_opening(f, np.ones((3, 3)))
    lab, n = nd.label(f); sizes = nd.sum(f, lab, range(1, n + 1))
    f = np.isin(lab, np.nonzero(sizes >= 150)[0] + 1)
    holes = nd.binary_fill_holes(f) & ~f          # fill only small holes (hatch speckle), not rooms
    hl, hn = nd.label(holes); hs = nd.sum(holes, hl, range(1, hn + 1))
    f |= np.isin(hl, np.nonzero(hs < 40)[0] + 1)
    return nd.binary_opening(f, np.ones((OP, OP)))  # drop door-leaf / window-frame stubs on wall faces


with_blue = refine(nonwhite | (blue & roi))
no_blue = refine(nonwhite)
# blue ink counts as wall only where it bridges a gap inside a wall (blue line crossing it),
# never where it sticks out of a wall face (dimension text/lines touching the wall)
bridge = nd.binary_closing(no_blue, np.ones((1, 7))) | nd.binary_closing(no_blue, np.ones((7, 1)))
fine = no_blue | (with_blue & bridge)
# the only hand fix: the "10" label circle touches the wall step of closet 10 and is drawn in wall-grey ink
fine[704:719, 358:371] = False
fine = nd.binary_opening(fine, np.ones((OP, OP)))
lab, n = nd.label(fine); sizes = nd.sum(fine, lab, range(1, n + 1))
print('components', sorted(sizes.astype(int)))
Image.fromarray((fine * 255).astype(np.uint8)).save(OUT)
print('wall px', fine.sum())
ov = a.copy().astype(np.uint8)
ov[fine] = (ov[fine] * 0.4 + np.array([255, 0, 0]) * 0.6).astype(np.uint8)
Image.fromarray(ov[580:1180, 85:410]).resize((325 * 3, 600 * 3), Image.NEAREST).save('overlay3x.png')
