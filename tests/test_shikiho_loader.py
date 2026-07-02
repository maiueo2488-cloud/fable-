from pathlib import Path

from jstock.ingestion.shikiho_loader import load_shikiho

SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample" / "dummy_shikiho.csv"


def test_load_shikiho_reads_all_rows():
    records = load_shikiho(SAMPLE_PATH)
    assert len(records) == 8


def test_load_shikiho_parses_numeric_fields():
    records = load_shikiho(SAMPLE_PATH)
    record = next(r for r in records if r.code == "1000")
    assert record.name == "テストA電機"
    assert record.sector == "電気機器"
    assert record.per == 15.2
    assert record.profit_growth == 12.1


def test_load_shikiho_skips_rows_without_code_or_name(tmp_path: Path):
    csv_path = tmp_path / "broken.csv"
    csv_path.write_text(
        "コード,銘柄名,業種,PER\n1000,テスト,電気機器,10.0\n,,,\n",
        encoding="utf-8-sig",
    )
    records = load_shikiho(csv_path)
    assert len(records) == 1
