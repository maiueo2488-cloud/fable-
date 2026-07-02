"""ファンダメンタルズスコアリング(純粋関数)。

複数指標をユニバース内でパーセンタイルランク化し、重み付き合計でスコア化する。
閾値フィルタではなく、相対順位に基づく説明可能なロジックを採用する。
欠損指標は重みを除外して残りの指標で再正規化する。
"""

import pandas as pd

from jstock.types import FundamentalScore, StockRecord

# "_inv" サフィックスは「低いほど良い」指標(PER, PBR)を反転して扱うことを示す
_WEIGHTS: dict[str, float] = {
    "profit_growth": 0.25,
    "roe": 0.20,
    "revenue_growth": 0.15,
    "dividend_yield": 0.10,
    "per_inv": 0.15,
    "pbr_inv": 0.15,
}


def _percentile_ranks(values: list[float | None]) -> list[float | None]:
    series = pd.Series(values, dtype="float64")
    ranks = series.rank(pct=True, na_option="keep")
    return [None if pd.isna(r) else float(r) for r in ranks]


def score_records(records: list[StockRecord]) -> list[FundamentalScore]:
    """ユニバース全体を渡し、各銘柄のFundamentalScoreを算出する。"""
    if not records:
        return []

    per_inv = [(-r.per if r.per is not None else None) for r in records]
    pbr_inv = [(-r.pbr if r.pbr is not None else None) for r in records]

    rank_columns: dict[str, list[float | None]] = {
        "profit_growth": _percentile_ranks([r.profit_growth for r in records]),
        "roe": _percentile_ranks([r.roe for r in records]),
        "revenue_growth": _percentile_ranks([r.revenue_growth for r in records]),
        "dividend_yield": _percentile_ranks([r.dividend_yield for r in records]),
        "per_inv": _percentile_ranks(per_inv),
        "pbr_inv": _percentile_ranks(pbr_inv),
    }

    results: list[FundamentalScore] = []
    for i, record in enumerate(records):
        sub_scores: dict[str, float] = {}
        total = 0.0
        total_weight = 0.0
        for metric, weight in _WEIGHTS.items():
            rank = rank_columns[metric][i]
            if rank is None:
                continue
            sub_scores[metric] = rank
            total += rank * weight
            total_weight += weight
        total_score = (total / total_weight) if total_weight > 0 else 0.0
        results.append(
            FundamentalScore(code=record.code, total_score=total_score, sub_scores=sub_scores)
        )
    return results


def rank_stocks(scores: list[FundamentalScore]) -> list[FundamentalScore]:
    """スコア降順でソートする。"""
    return sorted(scores, key=lambda s: s.total_score, reverse=True)
