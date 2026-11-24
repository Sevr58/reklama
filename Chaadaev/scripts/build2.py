import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
SB = Path(__file__).parent; sys.path.insert(0, str(SB))
from data_two import V
from fx import winterize, snowman

IDX = json.load(open(SB / "index.json"))
OUT = SB / "out_two"; OUT.mkdir(exist_ok=True)
GREEN, MINT, CREAM, INK, GREY, RED = (28, 58, 40), (152, 214, 190), (246, 243, 236), (30, 34, 32), (110, 118, 114), (178, 48, 44)
B = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", s)
R = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", s)
FW, FH, GAP, COLS, M = 880, 495, 40, 2, 50

def crop(im, fx, fy, zoom):
    W, H = im.size; tw = W; th = int(W * FH / FW)
    if th > H: th = H; tw = int(H * FW / FH)
    tw, th = int(tw / zoom), int(th / zoom)
    x = int((W - tw) * fx); y = int((H - th) * fy)
    return im.crop((x, y, x + tw, y + th)).resize((FW, FH), Image.LANCZOS)

def shadow_text(img, xy, text, f, anchor="mm", fill="white"):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.multiline_text(xy, text, font=f, fill=(0, 0, 0, 210), anchor=anchor, align="center", spacing=10)
    lay = lay.filter(ImageFilter.GaussianBlur(6)); img.paste(lay, (0, 0), lay)
    ImageDraw.Draw(img).multiline_text(xy, text, font=f, fill=fill, anchor=anchor, align="center", spacing=10)

def frame_img(fr):
    if fr.get("pack"):
        im = Image.new("RGB", (FW, FH), GREEN); d = ImageDraw.Draw(im); l = fr["pack"].split("\n")
        d.text((FW // 2, FH // 2 - 45), l[0].upper(), font=B(52), fill=MINT, anchor="mm")
        d.text((FW // 2, FH // 2 + 35), l[1], font=R(30), fill=CREAM, anchor="mm")
        d.text((FW // 2, FH - 50), "логотип · телефон · сайт", font=R(20), fill=(120, 160, 140), anchor="mm"); return im
    im = Image.open(IDX[fr["img"]]).convert("RGB"); im.thumbnail((2400, 2400))
    if fr.get("win"): im = winterize(im, fr["win"])
    im = crop(im, fr.get("fx", 0.5), fr.get("fy", 0.5), fr.get("zoom", 1.0))
    if fr.get("snowman"): im = snowman(im, *fr["snowman"])
    if fr.get("title"):
        im = ImageEnhance.Brightness(im).enhance(0.82); shadow_text(im, (FW // 2, FH // 2), fr["title"], R(42))
    return im

def wrap(d, text, f, width):
    out, line = [], ""
    for w in text.split():
        t = (line + " " + w).strip()
        if d.textlength(t, font=f) <= width: line = t
        else: out.append(line); line = w
    return out + [line]

def build(v):
    fr_ = v["frames"]; rows = (len(fr_) + COLS - 1) // COLS; CARD = FH + 300; HEAD = 260
    W = M * 2 + FW * COLS + GAP; H = HEAD + rows * (CARD + GAP) + 70
    s = Image.new("RGB", (W, H), CREAM); d = ImageDraw.Draw(s)
    d.rectangle([0, 0, W, HEAD - 40], fill=GREEN)
    d.text((M, 38), f"«{v['name']}» ★  · подробная раскадровка", font=B(54), fill=MINT)
    for i, l in enumerate(wrap(d, v["idea"], R(26), W - 2 * M)[:3]): d.text((M, 115 + i * 34), l, font=R(26), fill=CREAM)
    d.text((W - M, 50), "ЖК «Чаадаев» · 20 с · 16:9 · ЗИМА", font=R(24), fill=(150, 190, 170), anchor="ra")
    for i, fr in enumerate(fr_):
        x = M + (i % COLS) * (FW + GAP); y = HEAD + (i // COLS) * (CARD + GAP)
        d.rectangle([x - 2, y - 2, x + FW + 2, y + CARD], fill="white", outline=(215, 210, 200), width=2)
        s.paste(frame_img(fr), (x, y))
        d.rectangle([x, y, x + 200, y + 44], fill=GREEN); d.text((x + 14, y + 8), f"{i + 1} · {fr['t']}", font=B(22), fill=MINT)
        ty = y + FH + 16
        for l in wrap(d, fr["a"], R(24), FW - 30)[:4]: d.text((x + 16, ty), l, font=R(24), fill=INK); ty += 32
        ty = y + FH + 160
        d.text((x + 16, ty), "КАМЕРА: " + fr["c"], font=R(20), fill=GREY)
        d.text((x + 16, ty + 30), "ЗВУК: " + fr["s"], font=R(20), fill=GREY)
        if fr.get("title"): d.text((x + 16, ty + 60), "ТИТР: " + fr["title"].replace("\n", " "), font=B(20), fill=GREEN)
        if fr.get("d") and fr["d"] != "—":
            for k, l in enumerate(wrap(d, "▸ " + fr["d"], R(19), FW - 30)[:2]): d.text((x + 16, ty + 90 + k * 25), l, font=R(19), fill=RED)
    d.text((M, H - 50), "Кадры — рендеры ЖК. Лес в окнах переведён в зиму обработкой, снеговик дорисован схематично. Герои и действие — по подписи.", font=R(20), fill=GREY)
    p = OUT / f"{v['name']}_раскадровка_зима.jpg"; s.save(p, quality=90); return p

paths = [build(v) for v in V]
pages = [Image.open(p).convert("RGB") for p in paths]
pages[0].save(OUT / "Чаадаев_Шишка_и_Эстафета_зима.pdf", save_all=True, append_images=pages[1:], resolution=150)
for p in paths: print(p, Image.open(p).size)
