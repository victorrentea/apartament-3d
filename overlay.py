import numpy as np
from PIL import Image
from scipy import ndimage as nd
a=np.asarray(Image.open('original.jpg').convert('RGB')).astype(float)
r=np.asarray(Image.open('render.png').convert('L'))<128
o=a.copy(); o[r]=o[r]*0.35+np.array([0,200,0])*0.65
edge=r & ~nd.binary_erosion(r)
o[edge]=(255,0,0)
big=np.asarray(Image.fromarray(o.astype(np.uint8)[580:1180,85:410]).resize((1300,2400),Image.NEAREST))
Image.fromarray(big[0:1200]).save('ov_top.png'); Image.fromarray(big[1200:]).save('ov_bot.png')
