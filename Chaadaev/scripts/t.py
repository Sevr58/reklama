import json; from PIL import Image; from fx import winterize, snowman
idx = json.load(open("index.json"))
im = Image.open(idx[40]).convert("RGB"); im.thumbnail((900, 900)); print(im.size)
winterize(im, (0.05, 0.0, 0.95, 0.72)).save("t40.jpg")
im = Image.open(idx[46]).convert("RGB"); im.thumbnail((900, 900)); winterize(im, (0.45, 0.0, 1, 0.55)).save("t46.jpg")
im = Image.open(idx[66]).convert("RGB"); im.thumbnail((1200, 1200)); print(im.size); snowman(im, 560, 620, 330).save("t66.jpg")
