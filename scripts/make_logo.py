import pathlib
import sys
import urllib.request

import numpy as np
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
CACHE = ROOT / ".cache" / "fonts"
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/spectral/Spectral-Light.ttf"
WORD = "Обжиг"

GLAZE = "#1E4D41"
SOOT = "#161A19"
CHAMOTTE = "#E4DFD6"

D = 84.0
GAP = 25.0
BASELINE = D / 2 + 33.0
FONT_SCALE = 0.1
TRACKING = -2.0


def ensure_font():
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "Spectral-Light.ttf"
    if not path.exists():
        urllib.request.urlretrieve(FONT_URL, path)
    return path


def bezier(p0, p1, p2, p3, t):
    t = t[:, None]
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def catmull_to_bezier(pts):
    pts = np.asarray(pts, float)
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        out.append((p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6, p2))
    return out


def fmt(p):
    return f"{p[0]:.2f},{p[1]:.2f}"


def cone_path(base=(47, 80), p1=(47, 44), p2=(50, 24), tip=(66, 30), w0=20.0, n=9):
    p0, p1, p2, p3 = (np.array(p, float) for p in (base, p1, p2, tip))
    ts = np.linspace(0, 1, 400)
    c = bezier(p0, p1, p2, p3, ts)
    d = np.gradient(c, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    nrm = np.stack([-d[:, 1], d[:, 0]], 1)
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    s /= s[-1]
    w = w0 / 2 * (1 - s)
    left = c - nrm * w[:, None]
    right = c + nrm * w[:, None]
    idx = np.linspace(0, 399, n).astype(int)
    pts = np.concatenate([left[idx], right[idx][::-1][1:]])
    segs = catmull_to_bezier(pts)
    return f"M{fmt(pts[0])} " + " ".join(f"C{fmt(a)} {fmt(b)} {fmt(p)}" for a, b, p in segs) + " Z"


def measure_positions(font_path):
    html = f"""<!doctype html><meta charset="utf-8">
    <style>@font-face{{font-family:W;src:url('{font_path.as_uri()}')}}
    body{{margin:0}} #w{{font:1000px/1 W;white-space:nowrap;letter-spacing:0;font-kerning:normal}}</style>
    <div id="w">{WORD}</div>"""
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 4000, "height": 1200})
        pg.set_content(html)
        pg.wait_for_function("document.fonts.status==='loaded'")
        xs = pg.evaluate("""() => {
            const n = document.getElementById('w').firstChild;
            const r = document.createRange();
            const out = [];
            for (let i = 0; i < n.length; i++) { r.setStart(n, i); r.setEnd(n, i + 1); out.push(r.getBoundingClientRect().left); }
            return out;
        }""")
        b.close()
    return [x - xs[0] for x in xs]


def glyph_path(font, glyph_set, name, tx, ty, scale):
    pen = SVGPathPen(glyph_set, ntos=lambda v: f"{v:.2f}")
    tpen = TransformPen(pen, (scale, 0, 0, -scale, tx, ty))
    glyph_set[name].draw(tpen)
    return pen.getCommands()


def wordmark_paths(font_path, x0, baseline):
    font = TTFont(font_path)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    xs = measure_positions(font_path)
    paths = []
    width = 0.0
    for i, ch in enumerate(WORD):
        name = cmap[ord(ch)]
        tx = x0 + (xs[i] + TRACKING * i) * FONT_SCALE
        paths.append(glyph_path(font, gs, name, tx, baseline, FONT_SCALE))
        xmax = font["glyf"][name].xMax if name in font["glyf"].keys() else font["hmtx"][name][0]
        width = max(width, tx + xmax * FONT_SCALE - 0)
    return " ".join(paths), width


def svg(view_w, view_h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {view_w:.2f} {view_h:.2f}" role="img" aria-label="{title}">\n'
            f'{body}\n</svg>\n')


def main():
    font_path = ensure_font()
    cone = cone_path()
    disc = "M50,0 A50,50 0 1,1 50,100 A50,50 0 1,1 50,0 Z"
    out = ROOT / "logo"
    out.mkdir(exist_ok=True)

    (out / "logo-mark.svg").write_text(svg(100, 100,
        f'  <circle cx="50" cy="50" r="50" fill="{GLAZE}"/>\n  <path d="{cone}" fill="{CHAMOTTE}"/>', "Обжиг — знак"), encoding="utf-8")
    (out / "logo-mark-mono.svg").write_text(svg(100, 100,
        f'  <path d="{disc} {cone}" fill="{SOOT}" fill-rule="evenodd"/>', "Обжиг — знак, одноцветный"), encoding="utf-8")

    s = D / 100
    x0 = D + GAP
    word, width = wordmark_paths(font_path, x0, BASELINE)
    view_w = round(width + 0.0, 2)
    view_h = D
    mark_color = (f'  <g transform="translate(0 0) scale({s:.4f})">\n'
                  f'    <circle cx="50" cy="50" r="50" fill="{GLAZE}"/>\n    <path d="{cone}" fill="{CHAMOTTE}"/>\n  </g>\n')
    (out / "logo.svg").write_text(svg(view_w, view_h,
        mark_color + f'  <path d="{word}" fill="{SOOT}"/>', "Обжиг — студия керамики"), encoding="utf-8")
    for name, color, title in (("logo-mono.svg", SOOT, "одноцветный"), ("logo-inverse.svg", CHAMOTTE, "для тёмного фона")):
        body = (f'  <path d="{disc} {cone}" fill="{color}" fill-rule="evenodd" transform="scale({s:.4f})"/>\n'
                f'  <path d="{word}" fill="{color}"/>')
        (out / name).write_text(svg(view_w, view_h, body, f"Обжиг — логотип, {title}"), encoding="utf-8")
    print(f"logo viewBox {view_w} x {view_h}")


if __name__ == "__main__":
    main()
