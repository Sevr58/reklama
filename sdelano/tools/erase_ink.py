"""Стирает чернила заданного цвета внутри многоугольника, закрашивает бумагу (cv2.inpaint)
и возвращает зерно бумаги шумом той же силы.
usage: erase_ink.py src dst blue|green|any "x,y x,y ...;x,y ..." [dilate]"""
import sys, cv2, numpy as np
src, dst, kind, poly = sys.argv[1:5]
dil = int(sys.argv[5]) if len(sys.argv) > 5 else 4
polys = [np.array([list(map(int, p.split(','))) for p in q.split()], np.int32) for q in poly.split(';')]
im = cv2.imread(src)
b, g, r = [im[..., i].astype(int) for i in range(3)]
if kind == 'blue':
    m = (b > r + 25) & (b > g + 10)
elif kind == 'green':
    m = (g > r + 30) & (g > b + 20)
else:  # any: всё, что не почти белое
    m = im.min(axis=2) < int(__import__("os").environ.get("THR", 238))
area = np.zeros(m.shape, np.uint8); cv2.fillPoly(area, polys, 255)
mask = ((m & (area > 0)) * 255).astype(np.uint8)
mask = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=dil)
mask[area == 0] = 0
out = cv2.inpaint(im, mask, 5, cv2.INPAINT_TELEA).astype(np.float32)
# зерно бумаги: высокие частоты чистой бумаги вокруг (внутри области, вне маски)
hp = im.astype(np.float32) - cv2.GaussianBlur(im, (0, 0), 2).astype(np.float32)
ring = (area > 0) & (mask == 0) & (im.min(axis=2) > 150)
sd = hp[ring].std(axis=0)
rng = np.random.default_rng(1)
noise = cv2.GaussianBlur(rng.normal(0, 1, im.shape).astype(np.float32), (0, 0), 0.7)
noise = noise / noise.std() * sd
soft = cv2.GaussianBlur(mask, (0, 0), 1.5).astype(np.float32)[..., None] / 255
out = np.clip(out + noise * soft, 0, 255).astype(np.uint8)
print('masked px', int((mask > 0).sum()), 'grain sd', sd.round(2))
cv2.imwrite(dst, out)
