import pathlib
import sys

from playwright.sync_api import sync_playwright
from pypdf import PdfReader, PdfWriter

ROOT = pathlib.Path(__file__).resolve().parent.parent


def open_page(browser, path, width, height, dsf=1):
    page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=dsf)
    page.goto(pathlib.Path(path).resolve().as_uri(), wait_until="networkidle")
    page.wait_for_function("document.fonts.status === 'loaded'")
    page.evaluate("async () => { await document.fonts.ready; const imgs = [...document.images]; await Promise.all(imgs.map(i => i.complete ? null : new Promise(r => { i.onload = r; i.onerror = r; }))); }")
    page.wait_for_timeout(250)
    return page


def shot(browser, src, out, width, height, selector=None, dsf=1, full_page=False):
    page = open_page(browser, src, width, height, dsf)
    out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    if selector:
        page.locator(selector).screenshot(path=str(out))
    else:
        page.screenshot(path=str(out), full_page=full_page)
    page.close()
    print("png", out.relative_to(ROOT))


def pdf(browser, src, out, width, height, trim_mm=None, **kw):
    page = open_page(browser, src, width, height)
    page.emulate_media(media="print")
    page.wait_for_timeout(100)
    out = ROOT / out
    page.pdf(path=str(out), print_background=True, prefer_css_page_size=True, **kw)
    page.close()
    if trim_mm:
        set_page_size(out, *trim_mm)
    print("pdf", out.relative_to(ROOT))


def set_page_size(path, w_mm, h_mm):
    w, h = w_mm / 25.4 * 72, h_mm / 25.4 * 72
    reader = PdfReader(str(path))
    writer = PdfWriter()
    for p in reader.pages:
        top = float(p.mediabox.top)
        left = float(p.mediabox.left)
        for box in (p.mediabox, p.cropbox, p.trimbox, p.bleedbox, p.artbox):
            box.lower_left = (left, top - h)
            box.upper_right = (left + w, top)
        writer.add_page(p)
    with open(path, "wb") as f:
        writer.write(f)


JOBS = {
    "cards": lambda b: (
        shot(b, "src/cards/card.html", "cards/card-front.png", 1063, 1300, "#front"),
        shot(b, "src/cards/card.html", "cards/card-back.png", 1063, 1300, "#back"),
        pdf(b, "src/cards/card.html", "cards/business-card.pdf", 1063, 1300, trim_mm=(90, 50)),
    ),
    "social": lambda b: [shot(b, f"src/social/post-0{i}.html", f"social/post-0{i}.png", 1080, 1350) for i in range(1, 7)]
    + [shot(b, f"src/social/story-0{i}.html", f"social/story-0{i}.png", 1080, 1920) for i in range(1, 3)],
    "sheets": lambda b: (
        shot(b, "src/sheets/palette.html", "palette.png", 1800, 1100),
        shot(b, "src/sheets/typography.html", "typography.png", 1800, 1250),
        shot(b, "src/sheets/logo-light.html", "logo/logo-on-light.png", 1600, 700),
        shot(b, "src/sheets/logo-dark.html", "logo/logo-on-dark.png", 1600, 700),
        shot(b, "src/sheets/mark-light.html", "logo/logo-mark-on-light.png", 800, 800),
        shot(b, "src/sheets/mark-dark.html", "logo/logo-mark-on-dark.png", 800, 800),
    ),
    "brandbook": lambda b: (
        pdf(b, "brandbook/index.html", "brandbook/brandbook.pdf", 1123, 794),
        shot(b, "brandbook/index.html", ".cache/brandbook-full.png", 1440, 900, full_page=True),
    ),
}


def main(names):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name in names or JOBS:
            JOBS[name](browser)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
