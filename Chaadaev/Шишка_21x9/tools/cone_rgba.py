import sys
from PIL import Image
from rembg import remove, new_session
full=Image.open(sys.argv[1]).convert('RGB')
c=full.crop((60,1460,940,1970)); r=remove(c,session=new_session('isnet-general-use'))
bb=r.getchannel('A').point(lambda v:255 if v>20 else 0).getbbox(); r=r.crop(bb); r.save(sys.argv[2]); print(r.size)
