from jstock.notify.discord_notifier import build_discovery_embed, build_embed
from jstock.types import CatalystSignal, DiscoveryPick, FundamentalScore, JQuantsFundamentals, StockPick, StockRecord


def test_build_embed_includes_key_metrics():
    record = StockRecord(code="1000", name="テストA電機", per=15.2, pbr=1.3, roe=10.5, profit_growth=12.1)
    score = FundamentalScore(code="1000", total_score=0.8)
    pick = StockPick(record=record, score=score, sector_momentum=None, news=None, rationale="テスト理由")

    embed = build_embed(pick)

    assert embed["title"] == "テストA電機 (1000)"
    assert embed["description"] == "テスト理由"
    field_names = [f["name"] for f in embed["fields"]]
    assert "PER" in field_names
    assert "ROE" in field_names


def test_build_embed_omits_missing_metrics():
    record = StockRecord(code="2000", name="データ不足株")
    score = FundamentalScore(code="2000", total_score=0.5)
    pick = StockPick(record=record, score=score, sector_momentum=None, news=None, rationale="r")

    embed = build_embed(pick)
    assert embed["fields"] == []


def test_build_discovery_embed_includes_signal_and_fundamentals():
    signal = CatalystSignal(
        code="1000",
        name="テストA電機",
        title="業績予想の上方修正に関するお知らせ",
        category="業績予想の上方修正",
        polarity="positive",
        pdf_url="https://example.com/a.pdf",
    )
    fundamentals = JQuantsFundamentals(
        code="1000", disclosure_date="2026-02-06", per=15.0, pbr=1.5, roe=12.0
    )
    pick = DiscoveryPick(signal=signal, fundamentals=fundamentals, sector_momentum=None, rationale="テスト理由")

    embed = build_discovery_embed(pick)

    assert embed["title"] == "テストA電機 (1000)"
    assert embed["description"] == "テスト理由"
    field_names = [f["name"] for f in embed["fields"]]
    assert "検知カテゴリ" in field_names
    assert "PER" in field_names
    assert "開示PDF" in field_names


def test_build_discovery_embed_shows_deficit_instead_of_negative_per():
    signal = CatalystSignal(
        code="6897", name="テストB", title="増益に関するお知らせ", category="増益", polarity="positive"
    )
    fundamentals = JQuantsFundamentals(code="6897", disclosure_date="2026-02-06", per=-9.0)
    pick = DiscoveryPick(signal=signal, fundamentals=fundamentals, sector_momentum=None, rationale="r")

    embed = build_discovery_embed(pick)
    per_field = next(f for f in embed["fields"] if f["name"] == "PER")
    assert per_field["value"] == "赤字(算出不可)"


def test_build_discovery_embed_omits_missing_fundamentals():
    signal = CatalystSignal(
        code="2000", name="データ不足株", title="株主優待の新設に関するお知らせ", category="株主優待の新設・拡充", polarity="positive"
    )
    pick = DiscoveryPick(signal=signal, fundamentals=None, sector_momentum=None, rationale="r")

    embed = build_discovery_embed(pick)
    field_names = [f["name"] for f in embed["fields"]]
    assert field_names == ["検知カテゴリ"]
