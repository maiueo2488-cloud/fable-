"""Discord通知。Embed整形は純粋関数、送信はI/O。"""

import requests

from jstock.discovery.fundamentals import market_cap_tier
from jstock.types import DiscoveryPick, StockPick

_COLOR_GOOD = 0x2ECC71
_COLOR_DISCOVERY = 0x3498DB


def build_embed(pick: StockPick) -> dict:
    record = pick.record
    fields = []
    if record.per is not None:
        fields.append({"name": "PER", "value": f"{record.per:.1f}倍", "inline": True})
    if record.pbr is not None:
        fields.append({"name": "PBR", "value": f"{record.pbr:.2f}倍", "inline": True})
    if record.roe is not None:
        fields.append({"name": "ROE", "value": f"{record.roe:.1f}%", "inline": True})
    if record.profit_growth is not None:
        fields.append({"name": "増益率", "value": f"{record.profit_growth:.1f}%", "inline": True})
    if pick.sector_momentum is not None:
        fields.append(
            {
                "name": "業種モメンタム",
                "value": f"{pick.sector_momentum.sector} (score {pick.sector_momentum.momentum_score:.2f})",
                "inline": False,
            }
        )
    if pick.news is not None and pick.news.catalyst_summary:
        fields.append({"name": "ニュース/開示", "value": pick.news.catalyst_summary, "inline": False})

    return {
        "title": f"{record.name} ({record.code})",
        "description": pick.rationale,
        "color": _COLOR_GOOD,
        "fields": fields,
        "footer": {"text": f"総合スコア: {pick.score.total_score:.2f}"},
    }


def build_discovery_embed(pick: DiscoveryPick) -> dict:
    """ニュース検知ベースの発掘パイプライン用Embed。"""
    signal = pick.signal
    fundamentals = pick.fundamentals
    fields = [{"name": "検知カテゴリ", "value": signal.category, "inline": True}]
    if fundamentals is not None:
        basis = "会社予想ベース" if fundamentals.is_forecast else "実績ベース"
        if fundamentals.per is not None:
            # PERは純利益が赤字だと負値になり「お得感」のように誤読されるため、赤字は明示する。
            per_text = "赤字(算出不可)" if fundamentals.per < 0 else f"{fundamentals.per:.1f}倍({basis})"
            fields.append({"name": "PER", "value": per_text, "inline": True})
        if fundamentals.pbr is not None:
            fields.append({"name": "PBR", "value": f"{fundamentals.pbr:.2f}倍", "inline": True})
        if fundamentals.roe is not None:
            fields.append({"name": "ROE", "value": f"{fundamentals.roe:.1f}%({basis})", "inline": True})
        if fundamentals.disclosure_date is not None:
            fields.append({"name": "直近決算", "value": fundamentals.disclosure_date, "inline": True})
        if fundamentals.market_cap is not None:
            tier = market_cap_tier(fundamentals.market_cap)
            fields.append(
                {"name": "時価総額", "value": f"約{fundamentals.market_cap / 1e8:,.0f}億円({tier})", "inline": True}
            )
        if fundamentals.trading_value is not None:
            fields.append(
                {"name": "売買代金(直近日)", "value": f"約{fundamentals.trading_value / 1e8:,.1f}億円", "inline": True}
            )
    if pick.sector_momentum is not None:
        fields.append(
            {
                "name": "業種モメンタム",
                "value": f"{pick.sector_momentum.sector} (score {pick.sector_momentum.momentum_score:.2f})",
                "inline": False,
            }
        )
    if signal.pdf_url:
        fields.append({"name": "開示PDF", "value": signal.pdf_url, "inline": False})

    return {
        "title": f"{signal.name} ({signal.code})",
        "description": pick.rationale,
        "color": _COLOR_DISCOVERY,
        "fields": fields,
        "footer": {"text": f"重要度スコア: {signal.score:.1f}"},
    }


def send_to_discord(webhook_url: str, embeds: list[dict]) -> None:
    """Discord Webhookは1リクエストあたりEmbed最大10件のため分割送信する。"""
    for i in range(0, len(embeds), 10):
        chunk = embeds[i : i + 10]
        resp = requests.post(webhook_url, json={"embeds": chunk}, timeout=15)
        resp.raise_for_status()
