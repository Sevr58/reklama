import sys,os
from PIL import Image,ImageDraw,ImageFont
src,out,ids=sys.argv[1],sys.argv[2],sys.argv[3].split(',')
W,H,cols=480,300,4
files={f.split('.')[0]:f for f in os.listdir(src)}
rows=(len(ids)+cols-1)//cols
sh=Image.new('RGB',(W*cols,H*rows),'white');d=ImageDraw.Draw(sh)
f=ImageFont.load_default(size=28)
for i,k in enumerate(ids):
    im=Image.open(os.path.join(src,files[k])).convert('RGB');im.thumbnail((W-6,H-6))
    x,y=(i%cols)*W,(i//cols)*H;sh.paste(im,(x+3,y+3))
    d.rectangle([x+3,y+3,x+70,y+38],fill='black');d.text((x+8,y+5),k,fill='yellow',font=f)
sh.save(out,quality=85)
