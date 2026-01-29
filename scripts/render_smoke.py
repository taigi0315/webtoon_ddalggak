"""Simple smoke harness to render layout templates to SVG for quick visual checks.

Usage: python scripts/render_smoke.py
Writes SVGs into storage/media/smoke/
"""
from pathlib import Path
from app.config.loaders import load_layout_templates_9x16_v1

OUT_DIR = Path(__file__).resolve().parent.parent / "storage" / "media" / "smoke"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SVG_TEMPLATE = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 900 1600' width='450' height='800'>
  <rect width='100%' height='100%' fill='white' />
  {rects}
</svg>"""


def rect_for_panel(p, idx):
    x = int(p["x"] * 900)
    y = int(p["y"] * 1600)
    w = int(p["w"] * 900)
    h = int(p["h"] * 1600)
    color = f"hsl({(idx * 60) % 360} 70% 80%)"
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' fill='{color}' stroke='black' stroke-width='4'/>"


def render_template_to_svg(payload: dict) -> str:
    rects = []
    for idx, p in enumerate(payload.get("panels", []), start=1):
        rects.append(rect_for_panel(p, idx))
    return SVG_TEMPLATE.format(rects="\n  ".join(rects))


def main():
    templates = load_layout_templates_9x16_v1()
    for t in templates.templates:
        payload = {"template_id": t.template_id, "panels": [r.model_dump() for r in t.panels]}
        svg = render_template_to_svg(payload)
        out = OUT_DIR / f"{t.template_id}.svg"
        out.write_text(svg, encoding="utf-8")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
