"""ドメイン型定義。すべてイミュータブル(frozen dataclass)。"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StockRecord:
    code: str
    name: str
    sector: str | None = None
    revenue: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None
    bps: float | None = None
    per: float | None = None
    pbr: float | None = None
    roe: float | None = None
    revenue_growth: float | None = None
    profit_growth: float | None = None
    dividend_yield: float | None = None
    dividend_growth: float | None = None


@dataclass(frozen=True)
class FundamentalScore:
    code: str
    total_score: float
    sub_scores: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class SectorMomentum:
    sector: str
    return_1w: float
    return_1m: float
    volume_ratio: float
    momentum_score: float


@dataclass(frozen=True)
class NewsConfirmation:
    code: str
    headlines: tuple[str, ...] = ()
    catalyst_summary: str = ""


@dataclass(frozen=True)
class StockPick:
    record: StockRecord
    score: FundamentalScore
    sector_momentum: SectorMomentum | None
    news: NewsConfirmation | None
    rationale: str


@dataclass(frozen=True)
class CatalystSignal:
    """TDnet開示の見出しから検知した好材料/悪材料の候補。"""

    code: str
    name: str
    title: str
    category: str
    polarity: str  # "positive" | "negative"
    score: float = 0.0
    pdf_url: str | None = None


@dataclass(frozen=True)
class JQuantsFundamentals:
    """J-Quants /fins/summary + 直近終値から組み立てたファンダメンタルズ。

    通期決算以外の開示(1Q/2Q/3Q)では、sales/operating_income/net_income/epsは
    会社の通期予想値(is_forecast=True)を優先して使う。期初からの累計実績だけでは
    通期の一部しか反映されておらず、PER/ROEを実態より悪く見せてしまうため。
    """

    code: str
    disclosure_date: str | None
    sales: float | None = None
    operating_income: float | None = None
    net_income: float | None = None
    eps: float | None = None
    bps: float | None = None
    roe: float | None = None
    per: float | None = None
    pbr: float | None = None
    is_forecast: bool = False
    market_cap: float | None = None
    trading_value: float | None = None


@dataclass(frozen=True)
class DiscoveryPick:
    """ニュース検知ベースの発掘パイプラインにおける最終的な推奨1件。"""

    signal: CatalystSignal
    fundamentals: JQuantsFundamentals | None
    sector_momentum: SectorMomentum | None
    rationale: str
