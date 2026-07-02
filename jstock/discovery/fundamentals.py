"""J-Quants /fins/summary の生レスポンスから JQuantsFundamentals を組み立てる(純粋関数)。

注意(重要): /fins/summary の Sales/OP/NP/EPS は、CurPerType が "FY"(本決算)以外
(1Q/2Q/3Q)の場合、期初からの累計実績値であり、通期の一部しか反映していない。
これをそのままPER/ROEの計算に使うと、決算期の早い時期ほど実態より悪い値になる
(例: 1Q時点の累計EPSは通期の概ね1/4程度しかない)。
そのため、本決算以外では会社自身の通期予想(F〜系フィールド、無ければ来期予想NxF〜)
を優先して使う。J-Quants側のフィールド名は "NxFNp" のように大文字小文字が不統一
(NPだけ小文字pになる)ので、キー名を変更する際は注意すること。
"""

from jstock.types import JQuantsFundamentals

_PERIOD_MONTHS: dict[str, int] = {"1Q": 3, "2Q": 6, "3Q": 9, "FY": 12}


def _to_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _annualize(value: float | None, period_type: str | None) -> float | None:
    """累計実績を通期相当に単純換算する(会社予想が無い場合のフォールバック)。"""
    if value is None:
        return None
    months = _PERIOD_MONTHS.get(period_type or "")
    if not months:
        return None
    return value * 12 / months


def _select_annual_value(
    latest: dict, period_type: str | None, actual_key: str, forecast_key: str, next_forecast_key: str
) -> tuple[float | None, bool]:
    """通期相当の値と、それが会社予想ベースかどうかを返す。

    本決算ならそのまま実績を使う。四半期決算では、会社の通期予想(forecast_key)を
    最優先し、無ければ来期予想(next_forecast_key)、それも無ければ累計実績を
    単純に年率換算した値にフォールバックする。
    """
    if period_type == "FY":
        return _to_float(latest.get(actual_key)), False

    forecast = _to_float(latest.get(forecast_key))
    if forecast is not None:
        return forecast, True

    next_forecast = _to_float(latest.get(next_forecast_key))
    if next_forecast is not None:
        return next_forecast, True

    return _annualize(_to_float(latest.get(actual_key)), period_type), False


# 時価総額の目安(円)。TOPIX規模区分に近い分類で、大型投資家が実質的に参入できるかの目安にする。
_MARKET_CAP_TIERS: tuple[tuple[float, str], ...] = (
    (1_000_000_000_000, "超大型株"),
    (100_000_000_000, "大型株"),
    (30_000_000_000, "中型株"),
    (10_000_000_000, "小型株"),
)


def market_cap_tier(market_cap: float | None) -> str | None:
    """時価総額から規模区分を返す。機関投資家が参入しにくい超小型株を明示するための分類。"""
    if market_cap is None:
        return None
    for threshold, tier in _MARKET_CAP_TIERS:
        if market_cap >= threshold:
            return tier
    return "超小型株(機関投資家には参入しにくい規模)"


def build_fundamentals(
    code: str,
    summary_records: list[dict],
    latest_close: float | None,
    latest_volume: float | None = None,
) -> JQuantsFundamentals | None:
    """summary_records: /fins/summaryのレスポンス(開示日の古い順)。最新の開示を採用する。

    latest_volume(直近営業日の出来高)を渡すと、売買代金(流動性の目安)も算出する。
    """
    if not summary_records:
        return None

    latest = summary_records[-1]
    period_type = latest.get("CurPerType")

    sales, sales_is_forecast = _select_annual_value(latest, period_type, "Sales", "FSales", "NxFSales")
    operating_income, op_is_forecast = _select_annual_value(latest, period_type, "OP", "FOP", "NxFOP")
    net_income, np_is_forecast = _select_annual_value(latest, period_type, "NP", "FNP", "NxFNp")
    eps, eps_is_forecast = _select_annual_value(latest, period_type, "EPS", "FEPS", "NxFEPS")

    # BPS/Eq(自己資本)は決算期末時点のバランスシート残高で、累計/単期の区別が無いため調整不要。
    bps = _to_float(latest.get("BPS"))
    equity = _to_float(latest.get("Eq"))
    shares_outstanding = _to_float(latest.get("ShOutFY"))

    roe = (net_income / equity * 100) if net_income is not None and equity else None
    per = (latest_close / eps) if latest_close is not None and eps else None
    pbr = (latest_close / bps) if latest_close is not None and bps else None
    market_cap = (latest_close * shares_outstanding) if latest_close is not None and shares_outstanding else None
    trading_value = (latest_close * latest_volume) if latest_close is not None and latest_volume is not None else None

    return JQuantsFundamentals(
        code=code,
        disclosure_date=latest.get("DiscDate") or None,
        sales=sales,
        operating_income=operating_income,
        net_income=net_income,
        eps=eps,
        bps=bps,
        roe=roe,
        per=per,
        pbr=pbr,
        is_forecast=any((sales_is_forecast, op_is_forecast, np_is_forecast, eps_is_forecast)),
        market_cap=market_cap,
        trading_value=trading_value,
    )
