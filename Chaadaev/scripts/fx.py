import numpy as np, random
from PIL import Image, ImageDraw, ImageFilter

def winterize(im, box=(0, 0, 1, 1), strength=0.9, snow=True):
    """Перекрашивает зелень внутри box (доли кадра) в заснеженный лес."""
    a = np.asarray(im).astype(np.float32); H, W = a.shape[:2]
    x0, y0, x1, y1 = int(box[0]*W), int(box[1]*H), int(box[2]*W), int(box[3]*H)
    reg = a[y0:y1, x0:x1]; r, g, b = reg[..., 0], reg[..., 1], reg[..., 2]
    green = np.clip((g - b - 6) / 30, 0, 1) * (r <= g * 1.18)
    lum = 0.3*r + 0.59*g + 0.11*b
    amt = np.clip((lum - 30) / 110, 0, 1) * green * strength
    grey = np.stack([lum*0.85, lum*0.92, lum*1.05], -1)            # холодный серо-голубой вместо зелёного
    base = reg*(1-green[..., None]*0.8) + grey*(green[..., None]*0.8)
    white = np.array([236, 241, 248], np.float32)
    reg[:] = base*(1-amt[..., None]) + white*amt[..., None]
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    if snow:
        lay = Image.new("RGBA", out.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); rnd = random.Random(7)
        for _ in range(int((x1-x0)*(y1-y0)/4000)):
            x, y = rnd.randint(x0, x1), rnd.randint(y0, y1); s = rnd.choice([1, 1, 1, 2])
            d.ellipse([x-s, y-s, x+s, y+s], fill=(255, 255, 255, rnd.randint(120, 220)))
        lay = lay.filter(ImageFilter.GaussianBlur(0.8)); out.paste(lay, (0, 0), lay)
    return out

def snowman(im, x, y, h, nose=True):
    """Схематичный снеговик: низ в точке (x, y), высота h пикселей."""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.ellipse([x-h*0.32, y-h*0.06, x+h*0.32, y+h*0.06], fill=(120, 135, 160, 110))   # тень
    rs = [h*0.22, h*0.16, h*0.11]; cy = y
    centers = []
    for r in rs:
        cy -= r; centers.append((x, cy, r))
        for k in range(10, 0, -1):                                                   # объём: от голубого края к белому центру
            t = k / 10; c = int(205 + 45*(1-t))
            d.ellipse([x-r*t - (1-t)*r*0.25, cy-r*t-(1-t)*r*0.25, x+r*t-(1-t)*r*0.25, cy+r*t-(1-t)*r*0.25], fill=(c-8, c-3, min(255, c+6), 255))
        cy -= r*0.75
    hx, hy, hr = centers[2]
    for ex in (-0.35, 0.35): d.ellipse([hx+ex*hr-hr*0.08, hy-hr*0.3, hx+ex*hr+hr*0.08, hy-hr*0.14], fill=(30, 30, 30, 255))
    if nose:  # шишка
        d.polygon([(hx+hr*0.05, hy-hr*0.05), (hx+hr*0.75, hy+hr*0.1), (hx+hr*0.05, hy+hr*0.25)], fill=(110, 70, 40, 255))
        for i in range(4):
            px = hx+hr*(0.15+i*0.13); d.line([(px, hy), (px, hy+hr*0.2)], fill=(70, 42, 22, 255), width=2)
    bx, by, br = centers[1]
    d.line([(bx-br, by), (bx-br*2.0, by-br*0.8)], fill=(80, 55, 35, 255), width=4)
    d.line([(bx+br, by), (bx+br*2.0, by-br*0.9)], fill=(80, 55, 35, 255), width=4)
    lay = lay.filter(ImageFilter.GaussianBlur(0.6)); im.paste(lay, (0, 0), lay); return im
