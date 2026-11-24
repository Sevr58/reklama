import json, sys, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
sys.path.insert(0, str(Path(__file__).parent))
import importlib, os; MOD = os.environ.get("SB_DATA", "data"); V = importlib.import_module(MOD).V; TAG = "ЗИМА" if MOD == "data_winter" else ""

SB = Path(__file__).parent
IDX = json.load(open(SB / "index.json"))
OUT = SB / ("out_winter" if TAG else "out"); OUT.mkdir(exist_ok=True)
GREEN, MINT, CREAM, INK, GREY = (28, 58, 40), (152, 214, 190), (246, 243, 236), (30, 34, 32), (110, 118, 114)
F = "/usr/share/fonts/truetype/"
def font(name, size): return ImageFont.truetype(F + name, size)
B = lambda s: font("dejavu/DejaVuSans-Bold.ttf", s)
R = lambda s: font("dejavu/DejaVuSans.ttf", s)
FW, FH, GAP, COLS, M = 880, 495, 40, 2, 50

def crop169(p, fy, w=FW, h=FH):
    im = Image.open(p).convert("RGB")
    W, H = im.size; tw = W; th = int(W * h / w)
    if th > H: th = H; tw = int(H * w / h)
    x = (W - tw) // 2; y = int((H - th) * fy)
    return im.crop((x, y, x + tw, y + th)).resize((w, h), Image.LANCZOS)

def shadow_text(img, xy, text, f, anchor="mm", fill="white"):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.multiline_text(xy, text, font=f, fill=(0, 0, 0, 200), anchor=anchor, align="center", spacing=10)
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    img.paste(layer, (0, 0), layer)
    ImageDraw.Draw(img).multiline_text(xy, text, font=f, fill=fill, anchor=anchor, align="center", spacing=10)

def frame_img(fr):
    if fr.get("pack"):
        im = Image.new("RGB", (FW, FH), GREEN); d = ImageDraw.Draw(im)
        lines = fr["pack"].split("\n")
        d.text((FW // 2, FH // 2 - 40), lines[0].upper(), font=B(52), fill=MINT, anchor="mm")
        if len(lines) > 1: d.text((FW // 2, FH // 2 + 40), lines[1], font=R(32), fill=CREAM, anchor="mm")
        d.text((FW // 2, FH - 50), "логотип · телефон · сайт", font=R(20), fill=(120, 160, 140), anchor="mm")
        return im
    if fr.get("black"):
        im = Image.new("RGB", (FW, FH), (5, 5, 5))
        ImageDraw.Draw(im).text((FW // 2, FH // 2), "· тишина ·", font=R(28), fill=(90, 90, 90), anchor="mm"); return im
    if fr.get("split"):
        a, b = fr["split"]; half = FW // 2
        im = Image.new("RGB", (FW, FH))
        im.paste(crop169(IDX[a], fr["fy"], half, FH), (0, 0)); im.paste(crop169(IDX[b], fr["fy"], half, FH), (half, 0))
        d = ImageDraw.Draw(im); d.line([(half, 0), (half, FH)], fill="white", width=4)
        for x, t in ((half // 2, "ЦЕНТР"), (half + half // 2, "ЧААДАЕВ")):
            shadow_text(im, (x, FH - 34), t, B(24))
        return im
    im = crop169(IDX[fr["img"]], fr.get("fy", 0.5))
    if fr.get("spot"):
        x, y = int(fr["spot"][0] * FW), int(fr["spot"][1] * FH)
        glow = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(glow)
        d.ellipse([x - 55, y - 38, x + 55, y + 38], fill=(255, 245, 200, 230))
        glow = glow.filter(ImageFilter.GaussianBlur(14)); im.paste(glow, (0, 0), glow)
    if fr.get("title"):
        im = ImageEnhance.Brightness(im).enhance(0.8)
        shadow_text(im, (FW // 2, FH // 2), fr["title"], R(42))
    if fr.get("corner"):
        shadow_text(im, (FW - 30, 30), fr["corner"], B(34), anchor="ra", fill=MINT)
    return im

def wrap(d, text, f, width):
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=f) <= width: line = t
        else: out.append(line); line = w
    out.append(line); return out

def build(v):
    frames = v["frames"]; rows = (len(frames) + COLS - 1) // COLS
    CARD = FH + 230; HEAD = 230
    W = M * 2 + FW * COLS + GAP * (COLS - 1); H = HEAD + rows * (CARD + GAP) + 60
    sheet = Image.new("RGB", (W, H), CREAM); d = ImageDraw.Draw(sheet)
    d.rectangle([0, 0, W, HEAD - 40], fill=GREEN)
    d.text((M, 40), f"ВАРИАНТ {v['n']}. «{v['name']}»" + ("  ★" if v.get("star") else ""), font=B(54), fill=MINT)
    for i, l in enumerate(wrap(d, v["idea"], R(26), W - 2 * M)[:2]):
        d.text((M, 115 + i * 36), l, font=R(26), fill=CREAM)
    d.text((W - M, 52), "ЖК «Чаадаев» · 20 с · 16:9" + (" · ЗИМА" if TAG else ""), font=R(24), fill=(150, 190, 170), anchor="ra")
    for i, fr in enumerate(frames):
        x = M + (i % COLS) * (FW + GAP); y = HEAD + (i // COLS) * (CARD + GAP)
        d.rectangle([x - 2, y - 2, x + FW + 2, y + CARD], fill="white", outline=(215, 210, 200), width=2)
        sheet.paste(frame_img(fr), (x, y))
        d.rectangle([x, y, x + 190, y + 44], fill=GREEN)
        d.text((x + 14, y + 8), f"{i + 1} · {fr['t']}", font=B(22), fill=MINT)
        ty = y + FH + 16
        for l in wrap(d, fr["a"], R(24), FW - 30)[:3]:
            d.text((x + 16, ty), l, font=R(24), fill=INK); ty += 33
        ty = y + FH + 130
        d.text((x + 16, ty), "КАМЕРА: " + fr["c"], font=R(20), fill=GREY)
        d.text((x + 16, ty + 32), "ЗВУК: " + fr["s"], font=R(20), fill=GREY)
        if fr.get("title"):
            d.text((x + 16, ty + 64), "ТИТР: " + fr["title"].replace("\n", " "), font=B(20), fill=GREEN)
    d.text((M, H - 45), "Кадры — рендеры ЖК, подобраны как референс атмосферы. Действие и герои — по подписи.", font=R(20), fill=GREY)
    p = OUT / f"{v['n']:02d}_{v['name'].replace(' ', '_')}.jpg"; sheet.save(p, quality=88); return p

paths = [build(v) for v in V]
pages = [Image.open(p).convert("RGB") for p in paths]
pages[0].save(OUT / ("Чаадаев_ЗИМА_раскадровки_10_вариантов.pdf" if TAG else "Чаадаев_раскадровки_10_вариантов.pdf"), save_all=True, append_images=pages[1:], resolution=150)
for p in paths: print(p.name, Image.open(p).size)
