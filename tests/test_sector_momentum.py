import pandas as pd

from jstock.sector.sector_momentum import compute_sector_momentum


def _build_quotes(code: str, closes: list[float], volumes: list[float], start: str = "2024-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(closes), freq="D")
    return pd.DataFrame({"Code": code, "Date": dates, "Close": closes, "Volume": volumes})


def test_compute_sector_momentum_ranks_higher_growth_sector_first():
    rows = []
    for code in ["1000", "1001"]:
        closes = [100 + i * 2 for i in range(30)]
        volumes = [1000] * 20 + [3000] * 10
        rows.append(_build_quotes(code, closes, volumes))
    for code in ["2000", "2001"]:
        closes = [100.0] * 30
        volumes = [1000] * 30
        rows.append(_build_quotes(code, closes, volumes))

    quotes = pd.concat(rows, ignore_index=True)
    sector_by_code = {"1000": "成長業種", "1001": "成長業種", "2000": "停滞業種", "2001": "停滞業種"}

    result = compute_sector_momentum(quotes, sector_by_code, week_days=5, month_days=20)
    sectors = [r.sector for r in result]
    assert sectors[0] == "成長業種"


def test_compute_sector_momentum_empty_input_returns_empty_list():
    assert compute_sector_momentum(pd.DataFrame(), {}) == []
