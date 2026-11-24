import json, sys
from PIL import Image, ImageDraw, ImageFont
idx = json.load(open("index.json")); ids = [int(x) for x in sys.argv[2].split(",")]
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
W, H, C = 640, 420, 3; rows = (len(ids)+C-1)//C
s = Image.new("RGB", (W*C, H*rows), "black"); d = ImageDraw.Draw(s)
for k, i in enumerate(ids):
    im = Image.open(idx[i]).convert("RGB"); print(i, im.size); im.thumbnail((W, H)); x, y = (k%C)*W, (k//C)*H
    s.paste(im, (x, y)); d.rectangle([x, y, x+70, y+38], fill="red"); d.text((x+5, y+2), str(i), font=f, fill="white")
s.save(sys.argv[1], quality=85)
