from datetime import date

from jstock.types import SectorMomentum
from jstock.web.dashboard_builder import render_dashboard_html


def _momentum(sector: str, score: float) -> SectorMomentum:
    return SectorMomentum(
        sector=sector, return_1w=score, return_1m=score, volume_ratio=1.0 + score, momentum_score=score
    )


def test_render_dashboard_html_sorts_by_momentum_score_descending():
    momentum = [_momentum("停滞業種", -0.05), _momentum("成長業種", 0.10), _momentum("中間業種", 0.0)]

    html = render_dashboard_html(momentum, as_of=date(2026, 4, 1))

    assert html.index("成長業種") < html.index("中間業種") < html.index("停滞業種")


def test_render_dashboard_html_includes_delay_disclaimer_and_as_of_date():
    html = render_dashboard_html([_momentum("成長業種", 0.1)], as_of=date(2026, 4, 1))

    assert "12週間" in html
    assert "2026-04-01" in html


def test_render_dashboard_html_empty_input_renders_without_error():
    html = render_dashboard_html([], as_of=date(2026, 4, 1))

    assert "<html" in html
    assert "データを取得できませんでした" in html
