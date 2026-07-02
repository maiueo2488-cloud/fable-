"""四季報データ(CSV/Excel)の取り込み。"""

import math
from pathlib import Path

import pandas as pd

from jstock.ingestion.column_mapping import ColumnMapping, default_mapping
from jstock.types import StockRecord

_FLOAT_FIELDS = (
    "revenue",
    "operating_income",
    "net_income",
    "eps",
    "bps",
    "per",
    "pbr",
    "roe",
    "revenue_growth",
    "profit_growth",
    "dividend_yield",
    "dividend_growth",
)

_MISSING_TOKENS = {"", "-", "--", "---", "N/A", "nan", "なし"}


def _to_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).strip()
    if text in _MISSING_TOKENS:
        return None
    text = text.replace(",", "").replace("%", "").replace("倍", "").replace("円", "")
    try:
        return float(text)
    except ValueError:
        return None


def _row_to_record(row: pd.Series, mapping: ColumnMapping) -> StockRecord | None:
    code_col = mapping.source_column("code")
    name_col = mapping.source_column("name")
    if code_col is None or name_col is None:
        raise ValueError("code/name の列マッピングが設定されていません")

    code = row.get(code_col)
    name = row.get(name_col)
    if pd.isna(code) or pd.isna(name):
        return None

    values: dict[str, float | None] = {}
    for field_name in _FLOAT_FIELDS:
        col = mapping.source_column(field_name)
        values[field_name] = _to_float(row.get(col)) if col else None

    sector_col = mapping.source_column("sector")
    raw_sector = row.get(sector_col) if sector_col else None
    sector = None if raw_sector is None or pd.isna(raw_sector) else str(raw_sector).strip()

    return StockRecord(
        code=str(code).strip(),
        name=str(name).strip(),
        sector=sector,
        **values,
    )


def load_shikiho(path: Path, mapping: ColumnMapping | None = None) -> list[StockRecord]:
    """四季報CSV/Excelファイルを読み込み、StockRecordのリストに変換する。"""
    mapping = mapping or default_mapping()
    path = Path(path)

    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)

    records: list[StockRecord] = []
    for _, row in df.iterrows():
        record = _row_to_record(row, mapping)
        if record is not None:
            records.append(record)
    return records
