import pathlib
import shutil

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "brandbook" / "assets"


def downsize(src, dst, width):
    im = Image.open(ROOT / src).convert("RGB")
    h = round(im.height * width / im.width)
    im.resize((width, h), Image.LANCZOS).save(OUT / dst, optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("logo.svg", "logo-inverse.svg", "logo-mono.svg", "logo-mark.svg", "logo-mark-mono.svg"):
        shutil.copy(ROOT / "logo" / name, OUT / name)
    downsize("cards/card-front.png", "card-front.png", 900)
    downsize("cards/card-back.png", "card-back.png", 900)
    for i in range(1, 7):
        downsize(f"social/post-0{i}.png", f"post-0{i}.png", 540)
    for i in range(1, 3):
        downsize(f"social/story-0{i}.png", f"story-0{i}.png", 432)
    print("assets:", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
