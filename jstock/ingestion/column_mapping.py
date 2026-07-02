"""四季報データの列名を内部フィールド名に吸収するためのマッピング。

ユーザー提供ファイルの実際の列名は未確定。実データを受け取った時点で
DEFAULT_MAPPING を調整するか、load_shikiho() 呼び出し時に上書き用の
mapping を渡す。
"""

from dataclasses import dataclass, fields

from jstock.types import StockRecord

# 内部フィールド名 -> 想定される四季報CSV/Excelの列名
DEFAULT_MAPPING: dict[str, str] = {
    "code": "コード",
    "name": "銘柄名",
    "sector": "業種",
    "revenue": "売上高",
    "operating_income": "営業利益",
    "net_income": "純利益",
    "eps": "EPS",
    "bps": "BPS",
    "per": "PER",
    "pbr": "PBR",
    "roe": "ROE",
    "revenue_growth": "増収率",
    "profit_growth": "増益率",
    "dividend_yield": "配当利回り",
    "dividend_growth": "増配率",
}

_RECORD_FIELDS = {f.name for f in fields(StockRecord)}


@dataclass(frozen=True)
class ColumnMapping:
    mapping: dict[str, str]

    def source_column(self, field_name: str) -> str | None:
        return self.mapping.get(field_name)


def default_mapping() -> ColumnMapping:
    return ColumnMapping(mapping=dict(DEFAULT_MAPPING))


def custom_mapping(overrides: dict[str, str]) -> ColumnMapping:
    """DEFAULT_MAPPING に overrides を上書きしたマッピングを作る。

    overrides のキーは StockRecord のフィールド名でなければならない。
    """
    unknown = set(overrides) - _RECORD_FIELDS
    if unknown:
        raise ValueError(f"未知のフィールド名: {sorted(unknown)}")
    merged = dict(DEFAULT_MAPPING)
    merged.update(overrides)
    return ColumnMapping(mapping=merged)
