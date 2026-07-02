from unittest.mock import MagicMock, patch

import pandas as pd

from jstock.sector.jquants_client import (
    fetch_daily_quotes,
    fetch_listed_info,
    sector_by_code_from_listed_info,
)


def _fake_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    return resp


@patch("jstock.sector.jquants_client.requests.get")
def test_get_paginated_follows_pagination_key(mock_get: MagicMock):
    mock_get.side_effect = [
        _fake_response({"data": [{"Code": "10000"}], "pagination_key": "next"}),
        _fake_response({"data": [{"Code": "20000"}]}),
    ]
    df = fetch_listed_info("dummy-key")
    assert mock_get.call_count == 2
    assert list(df["Code"]) == ["10000", "20000"]


@patch("jstock.sector.jquants_client.requests.get")
def test_fetch_daily_quotes_renames_close_and_volume(mock_get: MagicMock):
    mock_get.return_value = _fake_response(
        {"data": [{"Code": "10000", "Date": "2026-06-19", "C": 1500.0, "Vo": 2000.0}]}
    )
    df = fetch_daily_quotes("dummy-key", "2026-06-19")
    assert "Close" in df.columns
    assert "Volume" in df.columns
    assert df.loc[0, "Close"] == 1500.0
    assert df.loc[0, "Volume"] == 2000.0


def test_sector_by_code_from_listed_info_maps_s33nm():
    listed_info = pd.DataFrame({"Code": ["10000", "20000"], "S33Nm": ["電気機器", "食料品"]})
    mapping = sector_by_code_from_listed_info(listed_info)
    assert mapping == {"10000": "電気機器", "20000": "食料品"}


def test_sector_by_code_from_listed_info_empty_input_returns_empty_dict():
    assert sector_by_code_from_listed_info(pd.DataFrame()) == {}
