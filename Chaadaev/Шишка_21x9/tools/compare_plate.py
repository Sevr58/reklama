import sys, numpy as np
from PIL import Image, ImageFilter, ImageOps
src,ed,out=sys.argv[1],sys.argv[2],sys.argv[3]
o=Image.open(src).convert('RGB'); e=Image.open(ed).convert('RGB')
W,H=e.size; W2=800; H2=round(W2*H/W)
es=np.asarray(e.resize((W2,H2)).convert('L'),dtype=np.float32); es=(es-es.mean())/es.std()
best=None
for s in np.arange(0.90,1.13,0.01):
    ow=round(W2*s); oh=round(ow*o.size[1]/o.size[0])
    if oh<H2*0.9: continue
    os_=np.asarray(o.resize((ow,oh)).convert('L'),dtype=np.float32)
    for dx in range(-40,41,4):
      for dy in range(-40,41,4):
        x0=(ow-W2)//2+dx; y0=(oh-H2)//2+dy
        if x0<0 or y0<0 or x0+W2>ow or y0+H2>oh: continue
        c=os_[y0:y0+H2,x0:x0+W2]; c=(c-c.mean())/c.std(); r=float(np.mean(c*es))
        if best is None or r>best[0]: best=(r,s,x0,y0,ow,oh)
r,s,x0,y0,ow,oh=best
k=o.size[0]/ow
oc=o.crop((round(x0*k),round(y0*k),round((x0+W2)*k),round((y0+H2)*k))).resize((W,H),Image.LANCZOS)
A=np.asarray(oc,dtype=np.float32);B=np.asarray(e,dtype=np.float32)
ga=(A.mean(2)-A.mean())/A.std(); gb=(B.mean(2)-B.mean())/B.std()
print('aligned corr %.3f (scale %.2f)'%(np.mean(ga*gb),s))
print('brightness %+.0f%%  contrast %+.0f%%  warmth R-B %.1f -> %.1f'%((B.mean()/A.mean()-1)*100,(B.std()/A.std()-1)*100,(A[...,0]-A[...,2]).mean(),(B[...,0]-B[...,2]).mean()))
# per-region structural corr grid 4x3
gh,gw=3,4
rows=[]
for i in range(gh):
    rows.append(' '.join('%.2f'%np.mean(ga[i*H//gh:(i+1)*H//gh,j*W//gw:(j+1)*W//gw]*gb[i*H//gh:(i+1)*H//gh,j*W//gw:(j+1)*W//gw]) for j in range(gw)))
print('region corr grid:\n  '+'\n  '.join(rows))
def edges(im): return ImageOps.autocontrast(im.convert('L').filter(ImageFilter.FIND_EDGES))
Image.merge('RGB',(edges(oc),edges(e),edges(e))).save(out+'_edges.jpg',quality=85)
sw=900; sh=round(sw*H/W)
side=Image.new('RGB',(sw*2+10,sh),'white'); side.paste(oc.resize((sw,sh)),(0,0)); side.paste(e.resize((sw,sh)),(sw+10,0)); side.save(out+'_side.jpg',quality=85)
