import pathlib

import pypdfium2 as pdfium
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screens"
BG = (228, 223, 214)


def fit(path, width):
    im = Image.open(ROOT / path).convert("RGB")
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def save(im, name, max_w=1600):
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(OUT / name, optimize=True)
    print(name, im.size, round((OUT / name).stat().st_size / 1024), "KB")


def strip(paths, width, gap, bg=BG):
    ims = [fit(p, width) for p in paths]
    h = max(i.height for i in ims)
    sheet = Image.new("RGB", (len(ims) * width + (len(ims) + 1) * gap, h + 2 * gap), bg)
    for k, im in enumerate(ims):
        sheet.paste(im, (gap + k * (width + gap), gap))
    return sheet


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    save(strip(["logo/logo-on-light.png", "logo/logo-on-dark.png"], 780, 20), "logo.png")
    save(fit("palette.png", 1600), "palette.png")
    save(fit("typography.png", 1600), "typography.png")
    save(strip(["cards/card-front.png", "cards/card-back.png"], 780, 20), "cards.png")
    posts = strip([f"social/post-0{i}.png" for i in range(1, 7)], 320, 16)
    save(posts, "social.png", 2200)
    save(strip(["social/story-01.png", "social/story-02.png"], 400, 20), "stories.png")
    full = Image.open(ROOT / ".cache" / "brandbook-full.png").convert("RGB")
    save(full.crop((0, 0, full.width, min(full.height, 2400))), "brandbook.png", 1400)

    cover = pdfium.PdfDocument(str(ROOT / "brandbook" / "brandbook.pdf"))[0].render(scale=1.5).to_pil().convert("RGB")
    G = 20
    W = 1600
    cov = cover.resize((900, round(cover.height * 900 / cover.width)), Image.LANCZOS)
    logo = fit("logo/logo-on-light.png", 640)
    card = fit("cards/card-front.png", 640)
    left_h = logo.height + G + card.height
    row1 = max(cov.height, left_h)
    pw = 250
    ph = round(1350 * pw / 1080)
    canvas = Image.new("RGB", (W, G + row1 + G + ph + G), BG)
    canvas.paste(logo, (G, G + (row1 - left_h) // 2))
    canvas.paste(card, (G, G + (row1 - left_h) // 2 + logo.height + G))
    canvas.paste(cov, (W - 900 - G, G + (row1 - cov.height) // 2))
    y2 = G + row1 + G
    x = G
    for i in range(1, 7):
        canvas.paste(fit(f"social/post-0{i}.png", pw), (x, y2))
        x += pw + 12
    save(canvas, "overview.png")


if __name__ == "__main__":
    main()
