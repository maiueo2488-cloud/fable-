"""J-Quants APIクライアント(I/O層)。

v1はリフレッシュトークンからidTokenを発行する方式だったが、2025年末のv2移行で
APIキーを`x-api-key`ヘッダーに渡すだけの方式に変更された。エンドポイントパスや
レスポンスのフィールド名も変更されている(例: Sector33CodeName -> S33Nm,
Close -> C, Volume -> Vo)。本実装は公式ドキュメント(jpx-jquants.com)で
確認済みのv2仕様に基づく。
"""

import time

import pandas as pd
import requests

_BASE_URL = "https://api.jquants.com/v2"
_MAX_RETRIES = 3
_RETRY_BACKOFF_SEC = 10.0


def _request_with_retry(url: str, api_key: str, params: dict[str, str]) -> requests.Response:
    """429(レート制限)時は短い待機を挟んでリトライする。"""
    resp = requests.get(url, headers={"x-api-key": api_key}, params=params, timeout=30)
    for attempt in range(_MAX_RETRIES):
        if resp.status_code != 429:
            return resp
        wait_sec = float(resp.headers.get("Retry-After", _RETRY_BACKOFF_SEC * (attempt + 1)))
        time.sleep(wait_sec)
        resp = requests.get(url, headers={"x-api-key": api_key}, params=params, timeout=30)
    return resp


def _get_paginated(
    path: str, api_key: str, params: dict[str, str] | None = None, tolerate_400: bool = False
) -> list[dict]:
    """tolerate_400=True の場合、契約範囲外の日付指定などによる400を空リストとして扱う。"""
    records: list[dict] = []
    query = dict(params or {})
    while True:
        resp = _request_with_retry(f"{_BASE_URL}{path}", api_key, query)
        if tolerate_400 and resp.status_code == 400:
            return records
        resp.raise_for_status()
        payload = resp.json()
        records.extend(payload.get("data", []))
        pagination_key = payload.get("pagination_key")
        if not pagination_key:
            break
        query["pagination_key"] = pagination_key
    return records


def fetch_listed_info(api_key: str) -> pd.DataFrame:
    return pd.DataFrame(_get_paginated("/equities/master", api_key))


def fetch_daily_quotes(api_key: str, date: str) -> pd.DataFrame:
    """date: 'YYYY-MM-DD' 形式。指定日の全銘柄の四本値を取得する。

    無料プランは契約範囲外の日付(直近約12週間など)を指定すると400を返すため、
    その場合は空のDataFrameとして扱う。
    """
    records = _get_paginated(
        "/equities/bars/daily", api_key, params={"date": date.replace("-", "")}, tolerate_400=True
    )
    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.rename(columns={"C": "Close", "Vo": "Volume"})


def fetch_price_history(api_key: str, code: str, from_date: str, to_date: str) -> pd.DataFrame:
    """指定銘柄の四本値を期間指定で取得する(code, date共に4桁/5桁いずれの表記も可)。"""
    records = _get_paginated(
        "/equities/bars/daily",
        api_key,
        params={"code": code, "from": from_date.replace("-", ""), "to": to_date.replace("-", "")},
        tolerate_400=True,
    )
    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.rename(columns={"C": "Close", "Vo": "Volume"})


def fetch_fundamentals_summary(api_key: str, code: str) -> list[dict]:
    """指定銘柄の決算サマリー(/fins/summary)を開示日の古い順で取得する。"""
    return _get_paginated("/fins/summary", api_key, params={"code": code}, tolerate_400=True)


def sector_by_code_from_listed_info(listed_info: pd.DataFrame) -> dict[str, str]:
    if listed_info.empty or "S33Nm" not in listed_info.columns:
        return {}
    return dict(zip(listed_info["Code"], listed_info["S33Nm"], strict=False))
