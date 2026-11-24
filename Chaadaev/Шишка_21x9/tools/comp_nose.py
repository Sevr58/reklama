import sys, numpy as np
from PIL import Image, ImageFilter, ImageDraw
v3=Image.open('snowman_nose_v3.png').convert('RGB')
nn=Image.open('snowman_FINAL_nonose.png').convert('RGB').resize(v3.size,Image.LANCZOS)
L=float(sys.argv[1]); ang=float(sys.argv[2]); cx,cy=int(sys.argv[3]),int(sys.argv[4]); out=sys.argv[5]
# 1) стереть старый нос: заплатка лица из версии без носа, мягкая маска-эллипс
mask=Image.new('L',v3.size,0); ImageDraw.Draw(mask).ellipse((505,352,620,468),fill=255); mask=mask.filter(ImageFilter.GaussianBlur(10))
base=Image.composite(nn,v3,mask)
base.crop((470,320,660,500)).resize((570,540)).save(out.replace('.png','_patch.jpg'))
# 2) шишка A, матовая
cone=Image.open(sys.argv[6]).convert('RGBA'); cone=cone.crop((0,0,735,cone.height))
arr=np.asarray(cone.convert('RGB')).astype(float); lum=arr.mean(2,keepdims=True)
hi=np.clip((lum-110)/80,0,1); arr=arr*(1-0.45*hi); g=arr.mean(2,keepdims=True); arr=(arr*0.85+g*0.15)*0.97
cone=Image.merge('RGBA',(*Image.fromarray(np.clip(arr,0,255).astype(np.uint8)).split(),cone.getchannel('A')))
s=L/cone.width; cone=cone.resize((int(cone.width*s),int(cone.height*s)),Image.LANCZOS).rotate(ang,expand=True,resample=Image.BICUBIC)
px,py=cx-cone.width//2,cy-cone.height//2
al=cone.getchannel('A').filter(ImageFilter.GaussianBlur(5)).point(lambda v:int(v*0.5))
res=base.copy(); res.paste(Image.new('RGB',cone.size,(80,95,120)),(px+9,py+11),al); res.paste(cone,(px,py),cone)
res.save(out); res.crop((cx-130,cy-110,cx+130,cy+110)).resize((780,660),Image.LANCZOS).save(out.replace('.png','_zoom.jpg'))
