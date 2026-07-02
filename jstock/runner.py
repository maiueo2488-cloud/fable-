"""オーケストレーション層。各層を呼び出すだけの薄い実装。"""

import time
from datetime import date, timedelta

import pandas as pd

from jstock.config import Config
from jstock.ingestion.shikiho_loader import load_shikiho
from jstock.news.news_confirmation import build_news_confirmation
from jstock.news.tdnet_client import fetch_recent_disclosures
from jstock.notify.discord_notifier import build_embed, send_to_discord
from jstock.scoring.fundamental_score import rank_stocks, score_records
from jstock.sector.jquants_client import (
    fetch_daily_quotes,
    fetch_listed_info,
    sector_by_code_from_listed_info,
)
from jstock.sector.sector_momentum import compute_sector_momentum
from jstock.types import FundamentalScore, NewsConfirmation, SectorMomentum, StockPick


def _build_rationale(
    score: FundamentalScore,
    sector_momentum: SectorMomentum | None,
    news: NewsConfirmation | None,
) -> str:
    parts = [f"ファンダメンタルズスコア {score.total_score:.2f}(ユニバース内パーセンタイル)"]
    if sector_momentum is not None and sector_momentum.momentum_score > 0:
        parts.append(f"業種「{sector_momentum.sector}」に資金流入の兆候")
    if news is not None and news.headlines:
        parts.append("直近の適時開示で裏付けあり")
    return "。".join(parts) + "。"


# J-Quantsの無料プランは直近約12週間分の株価データが配信対象外(実測で確認済み)。
# そのため「今日」を起点にすると確実に空振りするので、配信遅延を見込んだ日付を起点にする。
_FREE_PLAN_DELAY_DAYS = 90
# 日次リクエストを連続発行すると429(レート制限)になるため間隔を空ける(実測で確認済み)。
_REQUEST_INTERVAL_SEC = 1.5


def fetch_sector_momentum_map(
    config: Config, lookback_calendar_days: int = 35, anchor_delay_days: int = _FREE_PLAN_DELAY_DAYS
) -> dict[str, SectorMomentum]:
    """J-Quants APIキー未設定時は空dictを返す(セクター分析をスキップ)。"""
    if not config.jquants_api_key:
        return {}

    api_key = config.jquants_api_key
    listed_info = fetch_listed_info(api_key)
    sector_by_code = sector_by_code_from_listed_info(listed_info)

    anchor = date.today() - timedelta(days=anchor_delay_days)
    quotes_frames: list[pd.DataFrame] = []
    for offset in range(lookback_calendar_days):
        day = anchor - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        df = fetch_daily_quotes(api_key, day.isoformat())
        if not df.empty:
            quotes_frames.append(df)
        time.sleep(_REQUEST_INTERVAL_SEC)
    if not quotes_frames:
        return {}

    quotes = pd.concat(quotes_frames, ignore_index=True)
    return {m.sector: m for m in compute_sector_momentum(quotes, sector_by_code)}


def run_analysis(config: Config, top_n: int = 20, dry_run: bool = False) -> list[StockPick]:
    """四季報データを読み込み、スコアリング→セクター分析→ニュース確認→Discord通知まで実行する。

    dry_run=True の場合、J-Quants/TDnetへの外部通信とDiscord送信をすべて省略し、
    四季報データのみによるローカルなスコアランキングを返す(開発ループでの高速反復用)。
    """
    records = load_shikiho(config.shikiho_data_path)
    scores = rank_stocks(score_records(records))
    record_by_code = {r.code: r for r in records}

    sector_momentum_map = {} if dry_run else fetch_sector_momentum_map(config)

    picks: list[StockPick] = []
    for score in scores[:top_n]:
        record = record_by_code[score.code]
        sector_momentum = sector_momentum_map.get(record.sector) if record.sector else None

        if dry_run:
            news = None
        else:
            disclosures = fetch_recent_disclosures(record.code, date.today())
            news = build_news_confirmation(record.code, disclosures)

        picks.append(
            StockPick(
                record=record,
                score=score,
                sector_momentum=sector_momentum,
                news=news,
                rationale=_build_rationale(score, sector_momentum, news),
            )
        )

    if not dry_run and config.discord_webhook_url:
        send_to_discord(config.discord_webhook_url, [build_embed(p) for p in picks])

    return picks
