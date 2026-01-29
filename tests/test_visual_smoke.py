from scripts.render_smoke import render_template_to_svg
from app.config.loaders import get_layout_template


def test_render_template_to_svg_contains_rects():
    tpl = get_layout_template("9x16_3_vertical")
    payload = {"template_id": tpl.template_id, "panels": [p.model_dump() for p in tpl.panels]}
    svg = render_template_to_svg(payload)
    assert "<rect" in svg
