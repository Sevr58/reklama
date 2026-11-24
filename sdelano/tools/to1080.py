"""Масштаб до ширины 1920 (Lanczos) и центральная обрезка до 1920x1080. usage: to1080.py src dst"""
import sys, cv2
im = cv2.imread(sys.argv[1]); h, w = im.shape[:2]
nh = round(h * 1920 / w); im = cv2.resize(im, (1920, nh), interpolation=cv2.INTER_LANCZOS4)
y = (nh - 1080) // 2; im = im[y:y + 1080]
assert im.shape[:2] == (1080, 1920), im.shape
cv2.imwrite(sys.argv[2], im); print(sys.argv[2], im.shape)
