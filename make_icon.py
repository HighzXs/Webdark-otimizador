"""Gera icon.ico a partir de meme.jpg (calopsita sorridente)."""
from PIL import Image, ImageDraw

src = Image.open("meme.jpg").convert("RGB")
# recorte quadrado em volta da cabeça
crop = src.crop((55, 5, 435, 385)).resize((512, 512), Image.LANCZOS)

mask = Image.new("L", (512, 512), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, 511, 511), radius=110, fill=255)
img = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
img.paste(crop, (0, 0), mask)

img.resize((256, 256), Image.LANCZOS).save("icon.png")
img.save("icon.ico", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("icon.ico ok")
