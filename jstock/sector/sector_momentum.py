"""業種別モメンタム計算(純粋関数)。

J-Quantsの日次株価データから、業種ごとの相対的な価格・出来高モメンタムを算出し、
資金が向かっていそうな業種を判定する代理指標とする。
"""

import pandas as pd

from jstock.types import SectorMomentum


def _stock_stats(group: pd.DataFrame, week_days: int, month_days: int) -> pd.Series:
    closes = group["Close"].to_numpy()
    volumes = group["Volume"].to_numpy()
    if len(closes) < week_days + 1:
        return pd.Series({"return_1w": None, "return_1m": None, "volume_ratio": None})

    return_1w = closes[-1] / closes[-week_days - 1] - 1
    return_1m = closes[-1] / closes[-month_days - 1] - 1 if len(closes) > month_days else None

    recent_vol = volumes[-week_days:].mean()
    prior_vol = (
        volumes[-month_days:-week_days].mean() if len(volumes) > month_days else volumes[:-week_days].mean()
    )
    volume_ratio = (recent_vol / prior_vol) if prior_vol else None

    return pd.Series({"return_1w": return_1w, "return_1m": return_1m, "volume_ratio": volume_ratio})


def compute_sector_momentum(
    quotes: pd.DataFrame,
    sector_by_code: dict[str, str],
    week_days: int = 5,
    month_days: int = 20,
) -> list[SectorMomentum]:
    """quotes: columns = ["Code", "Date", "Close", "Volume"]。Code内でDate昇順を想定。"""
    if quotes.empty:
        return []

    df = quotes.sort_values(["Code", "Date"])
    per_stock = df.groupby("Code", group_keys=True).apply(
        lambda g: _stock_stats(g, week_days, month_days), include_groups=False
    )
    per_stock["Sector"] = [sector_by_code.get(code) for code in per_stock.index]
    per_stock = per_stock.dropna(subset=["return_1w", "Sector"])

    if per_stock.empty:
        return []

    sector_stats = per_stock.groupby("Sector").mean(numeric_only=True)

    results: list[SectorMomentum] = []
    for sector, row in sector_stats.iterrows():
        return_1w = float(row.get("return_1w") or 0.0)
        return_1m = float(row.get("return_1m") or 0.0)
        volume_ratio = float(row.get("volume_ratio") or 1.0)
        momentum_score = return_1w * 0.4 + return_1m * 0.3 + (volume_ratio - 1.0) * 0.3
        results.append(
            SectorMomentum(
                sector=str(sector),
                return_1w=return_1w,
                return_1m=return_1m,
                volume_ratio=volume_ratio,
                momentum_score=momentum_score,
            )
        )
    return sorted(results, key=lambda s: s.momentum_score, reverse=True)
