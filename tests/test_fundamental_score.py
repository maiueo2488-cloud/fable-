from jstock.scoring.fundamental_score import rank_stocks, score_records
from jstock.types import StockRecord


def _record(code: str, profit_growth: float, roe: float, per: float, pbr: float) -> StockRecord:
    return StockRecord(
        code=code,
        name=f"テスト{code}",
        profit_growth=profit_growth,
        roe=roe,
        per=per,
        pbr=pbr,
    )


def test_higher_profit_growth_and_roe_scores_higher():
    records = [
        _record("A", profit_growth=30.0, roe=20.0, per=10.0, pbr=1.0),
        _record("B", profit_growth=-5.0, roe=5.0, per=25.0, pbr=3.0),
    ]
    scores = {s.code: s for s in score_records(records)}
    assert scores["A"].total_score > scores["B"].total_score


def test_rank_stocks_sorts_descending():
    records = [
        _record("A", profit_growth=30.0, roe=20.0, per=10.0, pbr=1.0),
        _record("B", profit_growth=-5.0, roe=5.0, per=25.0, pbr=3.0),
        _record("C", profit_growth=10.0, roe=12.0, per=15.0, pbr=1.5),
    ]
    ranked = rank_stocks(score_records(records))
    scores_in_order = [s.total_score for s in ranked]
    assert scores_in_order == sorted(scores_in_order, reverse=True)


def test_missing_metrics_do_not_crash():
    records = [
        StockRecord(code="A", name="テストA"),
        StockRecord(code="B", name="テストB", profit_growth=10.0),
    ]
    scores = score_records(records)
    assert len(scores) == 2
    for s in scores:
        assert isinstance(s.total_score, float)


def test_empty_input_returns_empty_list():
    assert score_records([]) == []
