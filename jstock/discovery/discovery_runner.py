"""ニュース検知ベースの銘柄発掘パイプライン(オーケストレーション層)。

TDnetの当日開示を全件スキャンし、好材料キーワードに合致した銘柄候補に絞って、
J-Quantsのファンダメンタルズ・セクターモメンタムで裏付けを行う。四季報ファイルの
提供を前提とした jstock.runner とは別の経路で、ファイル不要で運用できる。
"""

import time
from datetime import date, timedelta

from jstock.config import Config
from jstock.discovery.fundamentals import build_fundamentals, market_cap_tier
from jstock.discovery.sent_log import load_sent_codes, record_sent_codes
from jstock.news.catalyst_classifier import find_positive_candidates
from jstock.news.tdnet_client import fetch_all_disclosures
from jstock.notify.discord_notifier import build_discovery_embed, send_to_discord
from jstock.runner import fetch_sector_momentum_map
from jstock.sector.jquants_client import (
    fetch_fundamentals_summary,
    fetch_listed_info,
    fetch_price_history,
    sector_by_code_from_listed_info,
)
from jstock.types import CatalystSignal, DiscoveryPick, JQuantsFundamentals, SectorMomentum

# J-Quants無料プランの株価配信遅延の見込み(jstock.runnerと同じ前提)。
_FREE_PLAN_DELAY_DAYS = 90
_REQUEST_INTERVAL_SEC = 1.0


def _latest_quote(api_key: str, code: str) -> tuple[float | None, float | None]:
    """直近の終値・出来高を返す((close, volume))。取得できなければ(None, None)。"""
    anchor = date.today() - timedelta(days=_FREE_PLAN_DELAY_DAYS)
    history = fetch_price_history(api_key, code, (anchor - timedelta(days=14)).isoformat(), anchor.isoformat())
    if history.empty:
        return None, None
    latest_row = history.sort_values("Date").iloc[-1]
    return float(latest_row["Close"]), float(latest_row["Volume"])


def _build_rationale(
    signal: CatalystSignal,
    fundamentals: JQuantsFundamentals | None,
    sector_momentum: SectorMomentum | None,
) -> str:
    parts = [f"好材料検知(スコア{signal.score:.1f}): {signal.category}「{signal.title}」"]
    if fundamentals is not None and fundamentals.per is not None:
        basis = "会社予想" if fundamentals.is_forecast else "実績"
        per_text = "赤字(算出不可)" if fundamentals.per < 0 else f"{fundamentals.per:.1f}倍({basis}ベース)"
        metric = f"PER {per_text}"
        if fundamentals.roe is not None:
            metric += f" / ROE {fundamentals.roe:.1f}%"
        parts.append(metric)
    if fundamentals is not None and fundamentals.market_cap is not None:
        tier = market_cap_tier(fundamentals.market_cap)
        parts.append(f"時価総額 約{fundamentals.market_cap / 1e8:,.0f}億円({tier})")
    if sector_momentum is not None and sector_momentum.momentum_score > 0:
        parts.append(f"業種「{sector_momentum.sector}」も資金流入の兆候")
    return "。".join(parts) + "。"


def discover_picks(
    config: Config,
    target_date: date | None = None,
    max_candidates: int = 10,
    dry_run: bool = False,
    include_sector_momentum: bool = False,
) -> list[DiscoveryPick]:
    """TDnet全件スキャン→好材料分類→ファンダメンタルズ/セクター裏付けを行う。

    dry_run=True の場合、J-Quantsへの追加照会とDiscord送信を省略し、検知した
    候補の一覧だけを返す(開発ループでの高速反復用)。

    include_sector_momentum=True にするとセクターモメンタムも合わせて取得するが、
    無料プランのレート制限(実測で25回連続呼び出し程度で429)に引っかかりやすいため
    既定はFalse。候補ごとのファンダメンタルズ取得(候補数×2回)のみなら問題ない。

    同じ日に複数回実行(定期実行と手動実行が被る等)しても、既にDiscordへ送信済みの
    コードは data/sent_signals.json に記録され、再送されない。
    """
    target_date = target_date or date.today()
    disclosures = fetch_all_disclosures(target_date)
    already_sent = load_sent_codes(target_date) if not dry_run else set()
    candidates = [c for c in find_positive_candidates(disclosures) if c.code not in already_sent][:max_candidates]

    if dry_run or not config.jquants_api_key:
        return [
            DiscoveryPick(
                signal=signal,
                fundamentals=None,
                sector_momentum=None,
                rationale=_build_rationale(signal, None, None),
            )
            for signal in candidates
        ]

    api_key = config.jquants_api_key
    sector_by_short_code: dict[str, str] = {}
    sector_momentum_map: dict[str, SectorMomentum] = {}
    if include_sector_momentum:
        listed_info = fetch_listed_info(api_key)
        sector_by_code = sector_by_code_from_listed_info(listed_info)
        sector_by_short_code = {code[:4]: sector for code, sector in sector_by_code.items()}
        sector_momentum_map = fetch_sector_momentum_map(config)

    picks: list[DiscoveryPick] = []
    for signal in candidates:
        summary_records = fetch_fundamentals_summary(api_key, signal.code)
        latest_close, latest_volume = _latest_quote(api_key, signal.code)
        fundamentals = build_fundamentals(signal.code, summary_records, latest_close, latest_volume)
        sector_momentum = sector_momentum_map.get(sector_by_short_code.get(signal.code, ""))

        picks.append(
            DiscoveryPick(
                signal=signal,
                fundamentals=fundamentals,
                sector_momentum=sector_momentum,
                rationale=_build_rationale(signal, fundamentals, sector_momentum),
            )
        )
        time.sleep(_REQUEST_INTERVAL_SEC)

    if config.discord_webhook_url:
        send_to_discord(config.discord_webhook_url, [build_discovery_embed(p) for p in picks])
        record_sent_codes(target_date, [p.signal.code for p in picks])

    return picks
