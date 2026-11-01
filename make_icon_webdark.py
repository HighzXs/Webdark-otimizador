"""Gera as opções de ícone do WebDark (desenhado por código, sem imagem de fora).

Uso:  python make_icon_webdark.py            -> icon_opcoes/opcao_A.png, B, C e folha.png (comparação)
      python make_icon_webdark.py A          -> grava icon.png e icon.ico com a opção A
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

W = 2048                                   # trabalha grande e reduz no fim (bordas lisas)
STOPS = [(0.0, (0x4f, 0xd1, 0xe6)), (0.38, (0x5a, 0xa3, 0xe0)), (0.7, (0x8f, 0x71, 0xd0)), (1.0, (0xb0, 0x43, 0xd1))]
BG_TOP, BG_BOT = (14, 14, 26), (4, 4, 9)


def lerp(a, b, t):
    return tuple(int(x + (y - x) * t) for x, y in zip(a, b))


def grad_color(p):
    for (p0, c0), (p1, c1) in zip(STOPS, STOPS[1:]):
        if p0 <= p <= p1:
            return lerp(c0, c1, (p - p0) / (p1 - p0))
    return STOPS[-1][1]


def horizontal_gradient(size, x0, x1):
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for x in range(size):
        d.line([(x, 0), (x, size)], fill=grad_color(min(max((x - x0) / (x1 - x0), 0), 1)))
    return img


def diagonal_gradient(size):
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for i in range(size * 2):
        d.line([(i, 0), (i - size, size)], fill=grad_color(min(i / (size * 2), 1)), width=2)
    return img


def tile():
    """Fundo: quadrado de cantos arredondados, escuro, com um leve brilho no alto."""
    m = Image.new("L", (W, W), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, W - 1, W - 1), radius=int(W * 0.225), fill=255)
    bg = Image.new("RGB", (W, W))
    d = ImageDraw.Draw(bg)
    for y in range(W):
        d.line([(0, y), (W, y)], fill=lerp(BG_TOP, BG_BOT, y / W))
    glow = Image.new("L", (W, W), 0)
    ImageDraw.Draw(glow).ellipse((W * 0.1, -W * 0.45, W * 0.9, W * 0.38), fill=70)
    glow = glow.filter(ImageFilter.GaussianBlur(W * 0.08))
    bg.paste(Image.new("RGB", (W, W), (90, 70, 200)), (0, 0), glow)
    out = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    out.paste(bg, (0, 0), m)
    # aro fino de degradê na borda (luz de contorno)
    inner = Image.new("L", (W, W), 0)
    k = int(W * 0.012)
    ImageDraw.Draw(inner).rounded_rectangle((k, k, W - 1 - k, W - 1 - k), radius=int(W * 0.225) - k, fill=255)
    ring = Image.eval(Image.composite(Image.new("L", (W, W), 0), m, inner), lambda v: int(v * 0.55))
    out.paste(diagonal_gradient(W), (0, 0), ring)
    return out, m


def stroke_mask(points, width, closed=False):
    m = Image.new("L", (W, W), 0)
    d = ImageDraw.Draw(m)
    pts = [(x * W, y * W) for x, y in points]
    d.line(pts + ([pts[0]] if closed else []), fill=255, width=int(width * W), joint="curve")
    r = width * W / 2
    for x, y in pts:
        d.ellipse((x - r, y - r, x + r, y + r), fill=255)
    return m


def paint_gradient(canvas, mask, x0=0.2, x1=0.8, glow=0.5):
    """Pinta a forma com o degradê do WebDark e um brilho suave atrás."""
    if glow:
        halo = mask.filter(ImageFilter.GaussianBlur(W * 0.025)).point(lambda v: int(v * glow))
        canvas.paste(horizontal_gradient(W, W * x0, W * x1), (0, 0), halo)
    canvas.paste(horizontal_gradient(W, W * x0, W * x1), (0, 0), mask)


def sparkle(cx, cy, r, color=(255, 255, 255)):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.2
        pts.append((cx * W + math.cos(a) * rr * W, cy * W + math.sin(a) * rr * W))
    return pts


W_POINTS = [(0.22, 0.30), (0.365, 0.70), (0.50, 0.46), (0.635, 0.70), (0.78, 0.30)]


def option_a():
    """W em degradê, limpo e grande."""
    img, _ = tile()
    paint_gradient(img, stroke_mask(W_POINTS, 0.118), glow=0.55)
    return img


def option_b():
    """W em degradê, um pouco menor, com uma faísca de brilho no canto (limpeza)."""
    img, _ = tile()
    small = [(0.20, 0.36), (0.34, 0.74), (0.47, 0.52), (0.60, 0.74), (0.74, 0.36)]
    paint_gradient(img, stroke_mask(small, 0.108), x0=0.18, x1=0.76)
    d = ImageDraw.Draw(img)
    d.polygon(sparkle(0.80, 0.24, 0.115), fill=(255, 255, 255, 255))
    d.polygon(sparkle(0.665, 0.165, 0.045), fill=(180, 235, 255, 255))
    return img


def option_c():
    """Anel de degradê com o W branco no meio."""
    img, _ = tile()
    ring = Image.new("L", (W, W), 0)
    rd = ImageDraw.Draw(ring)
    rd.ellipse((W * 0.14, W * 0.14, W * 0.86, W * 0.86), fill=255)
    rd.ellipse((W * 0.205, W * 0.205, W * 0.795, W * 0.795), fill=0)
    paint_gradient(img, ring, 0.14, 0.86, glow=0.45)
    w_small = [(0.34, 0.37), (0.42, 0.63), (0.50, 0.49), (0.58, 0.63), (0.66, 0.37)]
    d = ImageDraw.Draw(img)
    g = stroke_mask(w_small, 0.062)
    img.paste(Image.new("RGB", (W, W), (240, 244, 255)), (0, 0), g)
    return img


def save_options():
    os.makedirs("icon_opcoes", exist_ok=True)
    opts = {"A": option_a(), "B": option_b(), "C": option_c()}
    for k, im in opts.items():
        im.resize((1024, 1024), Image.LANCZOS).save(f"icon_opcoes/opcao_{k}.png")
    # folha de comparação: cada opção grande + em 64, 32 e 16 px (como aparece na barra de tarefas)
    sheet = Image.new("RGBA", (1500, 640), (28, 28, 38, 255))
    for i, (k, im) in enumerate(opts.items()):
        x = 30 + i * 490
        sheet.paste(im.resize((330, 330), Image.LANCZOS), (x, 30), im.resize((330, 330), Image.LANCZOS))
        sx = x
        for s in (64, 48, 32, 16):
            small = im.resize((s, s), Image.LANCZOS)
            sheet.paste(small, (sx, 400), small)
            sx += s + 18
        big = im.resize((128, 128), Image.LANCZOS)
        sheet.paste(big, (x + 340, 230), big)
    sheet.save("icon_opcoes/folha.png")
    return opts


def install(key):
    im = {"A": option_a, "B": option_b, "C": option_c}[key]().resize((1024, 1024), Image.LANCZOS)
    im.resize((256, 256), Image.LANCZOS).save("icon.png")
    im.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("icon.png e icon.ico gravados com a opção", key)


def install_from_image(path):
    """Usa uma imagem pronta (ex.: feita no Gemini) como ícone: corta quadrado e arredonda os cantos."""
    src = Image.open(path).convert("RGB")
    side = min(src.size)
    src = src.crop(((src.width - side) // 2, (src.height - side) // 2, (src.width + side) // 2, (src.height + side) // 2))
    big = src.resize((1024, 1024), Image.LANCZOS).convert("RGBA")
    mask = Image.new("L", (4096, 4096), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 4095, 4095), radius=int(4096 * 0.225), fill=255)
    big.putalpha(mask.resize((1024, 1024), Image.LANCZOS))
    big.resize((256, 256), Image.LANCZOS).save("icon.png")
    big.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print("icon.png e icon.ico gravados a partir de", path)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower().endswith((".jpg", ".jpeg", ".png")):
        install_from_image(sys.argv[1])
    elif len(sys.argv) > 1:
        install(sys.argv[1].upper())
    else:
        save_options()
        print("opções em icon_opcoes/")
