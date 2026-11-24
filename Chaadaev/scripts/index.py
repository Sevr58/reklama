import sys, json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
S = Path(sys.argv[1])
files = sorted([p for d in ["chaadaev_renders","chaadaev_interiors"] for p in (S/d).rglob("*") if p.suffix.lower() in (".jpg",".jpeg",".png") and "ПЛАН" not in p.name and "ортограф" not in p.name])
files += sorted((S/"vframes").glob("v*.jpg"))
json.dump([str(f) for f in files], open(S/"sb/index.json","w"), ensure_ascii=False, indent=0)
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
W,H,C = 320,180,6
for page in range(0, len(files), 36):
    chunk = files[page:page+36]; rows = (len(chunk)+C-1)//C
    sheet = Image.new("RGB",(W*C,H*rows),"black"); d = ImageDraw.Draw(sheet)
    for i,p in enumerate(chunk):
        im = Image.open(p).convert("RGB"); im.thumbnail((W,H)); x,y = (i%C)*W,(i//C)*H
        sheet.paste(im,(x,y)); d.rectangle([x,y,x+60,y+34],fill="red"); d.text((x+4,y+2),str(page+i),font=f,fill="white")
    sheet.save(S/f"sb/idx_{page//36}.jpg", quality=80)
print(len(files))
