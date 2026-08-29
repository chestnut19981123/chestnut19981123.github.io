"""Render the blog's SVG figures to PNG and probe key pixels for verification."""
import re
import shutil
import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ASSET_DIR = Path("/home/chestnut/projects/chestnut19981123.github.io/source/_posts/AI/系统提示词的解剖")
TOOLS_DIR = Path("/home/chestnut/projects/chestnut19981123.github.io/tools")
OUT_DIR = Path("/tmp/fig_check")
OUT_DIR.mkdir(exist_ok=True)

# SVG 源：fig 与文章同目录（博客直接引用），cover 是纯源文件，只用于生成 PNG
SVGS = {
    "fig-booklet.svg": ASSET_DIR,
    "fig-register.svg": ASSET_DIR,
    "fig-surgery.svg": ASSET_DIR,
    "cover.svg": TOOLS_DIR,
}


def render():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for name, src_dir in SVGS.items():
            path = src_dir / name
            # 按 SVG 文件声明的 width/height 设置 viewport，避免默认 1280x720 裁剪封面
            head = path.read_text()[:300]
            m = re.search(r'width="(\d+)" height="(\d+)"', head)
            page.set_viewport_size({"width": int(m.group(1)), "height": int(m.group(2))})
            page.goto(path.as_uri())
            page.wait_for_load_state("networkidle")
            page.screenshot(path=OUT_DIR / (name.replace(".svg", ".png")))
        browser.close()
    # cover.png 是博客 front matter 引用的成品，放进文章资源目录
    shutil.copy(OUT_DIR / "cover.png", ASSET_DIR / "cover.png")


def probe(name: str, points: dict[str, tuple[int, int]]):
    """Probe pixels at exact coordinates, checking ±2px neighborhood."""
    im = Image.open(OUT_DIR / name).convert("RGB")
    w, h = im.size
    print(f"--- {name} ({w}x{h}) ---")
    for label, (x, y) in points.items():
        if not (0 <= x < w and 0 <= y < h):
            print(f"  {label}: OUT OF RANGE ({x},{y})")
            continue
        c = im.getpixel((x, y))
        near = set()
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                near.add(im.getpixel((x + dx, y + dy)))
        print(f"  {label} ({x},{y}): {c}  ±2px附近 {sorted(near)[:3]}...{sorted(near)[-2:]}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "render":
        render()
    elif len(sys.argv) > 1 and sys.argv[1] == "probe":
        # probes are passed as JSON: {"fig-cache.svg": {"label": [x,y]}}
        import json
        probes = json.loads(sys.argv[2])
        for name, pts in probes.items():
            probe(name, pts)
    else:
        render()
