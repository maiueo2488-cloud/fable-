from jstock.discovery.fundamentals import build_fundamentals, market_cap_tier


def test_build_fundamentals_uses_actual_values_for_fy_disclosure():
    records = [
        {
            "DiscDate": "2026-02-06",
            "CurPerType": "FY",
            "Sales": "1000",
            "OP": "100",
            "NP": "80",
            "EPS": "10.0",
            "BPS": "50.0",
            "Eq": "800",
        }
    ]
    fundamentals = build_fundamentals("1000", records, latest_close=150.0)
    assert fundamentals is not None
    assert fundamentals.is_forecast is False
    assert fundamentals.roe == 10.0
    assert fundamentals.per == 15.0
    assert fundamentals.pbr == 3.0


def test_build_fundamentals_prefers_company_forecast_for_quarterly_disclosure():
    # 実データで発見した問題: 累計実績EPSは赤字でも、会社の通期予想EPSは黒字のケース
    # (ツインバード: 3Q累計EPS=-44.24, 会社の通期予想FEPS=+9.39)
    records = [
        {
            "DiscDate": "2026-01-14",
            "CurPerType": "3Q",
            "Sales": "9000",
            "OP": "-200",
            "NP": "-480",
            "EPS": "-44.24",
            "FSales": "13000",
            "FOP": "150",
            "FNP": "100",
            "FEPS": "9.39",
            "BPS": "500.0",
            "Eq": "5000",
        }
    ]
    fundamentals = build_fundamentals("6897", records, latest_close=85.0)
    assert fundamentals is not None
    assert fundamentals.is_forecast is True
    assert fundamentals.eps == 9.39
    assert fundamentals.net_income == 100
    assert fundamentals.per is not None and fundamentals.per > 0  # 黒字予想なのでPERも正の値になる


def test_build_fundamentals_falls_back_to_next_fy_forecast_when_current_forecast_missing():
    records = [
        {
            "DiscDate": "2026-05-08",
            "CurPerType": "FY",
            "EPS": "365.94",
            "FEPS": "",
            "NxFEPS": "264.95",
            "BPS": "2000.0",
            "Eq": "30000",
        }
    ]
    # FYなのでEPSは実績そのまま使う(NxFEPSにフォールバックしない)
    fundamentals = build_fundamentals("7203", records, latest_close=2700.0)
    assert fundamentals.eps == 365.94
    assert fundamentals.is_forecast is False


def test_build_fundamentals_annualizes_when_no_forecast_available():
    # 会社予想が無い場合のフォールバック: 1Q累計値を単純に12/3倍する
    records = [{"DiscDate": "2026-08-01", "CurPerType": "1Q", "NP": "100", "EPS": "5.0", "BPS": "50.0", "Eq": "1000"}]
    fundamentals = build_fundamentals("1000", records, latest_close=100.0)
    assert fundamentals.eps == 20.0  # 5.0 * 12/3
    assert fundamentals.net_income == 400.0  # 100 * 12/3
    assert fundamentals.is_forecast is False


def test_build_fundamentals_uses_latest_record_when_multiple():
    records = [
        {"DiscDate": "2025-02-06", "CurPerType": "FY", "EPS": "9.0", "BPS": "45.0", "Eq": "700"},
        {"DiscDate": "2026-02-06", "CurPerType": "FY", "EPS": "10.0", "BPS": "50.0", "Eq": "800"},
    ]
    fundamentals = build_fundamentals("1000", records, latest_close=100.0)
    assert fundamentals.disclosure_date == "2026-02-06"
    assert fundamentals.eps == 10.0


def test_build_fundamentals_returns_none_for_empty_records():
    assert build_fundamentals("1000", [], latest_close=100.0) is None


def test_build_fundamentals_handles_missing_values_gracefully():
    records = [{"DiscDate": "2026-02-06", "CurPerType": "FY", "Sales": "", "OP": "", "NP": "", "EPS": "", "BPS": "", "Eq": ""}]
    fundamentals = build_fundamentals("1000", records, latest_close=None)
    assert fundamentals is not None
    assert fundamentals.sales is None
    assert fundamentals.roe is None
    assert fundamentals.per is None


def test_build_fundamentals_computes_market_cap_and_trading_value():
    records = [
        {"DiscDate": "2026-02-06", "CurPerType": "FY", "EPS": "10.0", "BPS": "50.0", "Eq": "800", "ShOutFY": "1000000"}
    ]
    fundamentals = build_fundamentals("1000", records, latest_close=100.0, latest_volume=5000.0)
    assert fundamentals.market_cap == 100.0 * 1_000_000
    assert fundamentals.trading_value == 100.0 * 5000.0


def test_market_cap_tier_classifies_by_size():
    assert market_cap_tier(2_000_000_000_000) == "超大型株"
    assert market_cap_tier(500_000_000_000) == "大型株"
    assert market_cap_tier(50_000_000_000) == "中型株"
    assert market_cap_tier(15_000_000_000) == "小型株"
    assert market_cap_tier(5_000_000_000) == "超小型株(機関投資家には参入しにくい規模)"
    assert market_cap_tier(None) is None
