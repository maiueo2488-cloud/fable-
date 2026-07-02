"""TDnet(東証適時開示)取得(I/O層)。

公式の構造化APIは提供されていないため、TDnetの日次開示一覧ページ
(release.tdnet.info)を取得し、指定コードに該当する開示行を抽出する。

実ページ(2026-06-19分)を取得して構造を検証済み:
- 各開示行は <td class="kjTime/kjCode/kjName/kjTitle"> を持つ<tr>
- kjCodeは4桁コード+末尾0(市場区分桁)の5桁表記のため、先頭4桁のみを使う
- PDFリンクはサイトルート相対パスのため絶対URLに変換する
- レスポンスヘッダにcharsetが無くrequestsの自動判定が外れるため、明示的にUTF-8指定が必要
"""

import time
from datetime import date as date_cls
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

_LIST_URL = "https://www.release.tdnet.info/inbs/I_list_{page:03d}_{date}.html"
_PAGE_BASE_URL = "https://www.release.tdnet.info/inbs/"
_REQUEST_INTERVAL_SEC = 0.5


def _fetch_page(page: int, target_date: date_cls) -> str | None:
    url = _LIST_URL.format(page=page, date=target_date.strftime("%Y%m%d"))
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        resp.encoding = "utf-8"
        return resp.text
    except requests.RequestException:
        return None


def _parse_rows(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    disclosures: list[dict] = []
    for code_cell in soup.find_all("td", class_="kjCode"):
        row = code_cell.find_parent("tr")
        if row is None:
            continue
        title_cell = row.find("td", class_="kjTitle")
        if title_cell is None:
            continue
        time_cell = row.find("td", class_="kjTime")
        name_cell = row.find("td", class_="kjName")
        pdf_link = title_cell.find("a", href=True)

        raw_code = code_cell.get_text(strip=True)
        disclosures.append(
            {
                "time": time_cell.get_text(strip=True) if time_cell else "",
                "code": raw_code[:4],
                "name": name_cell.get_text(strip=True) if name_cell else "",
                "title": title_cell.get_text(strip=True),
                "pdf_url": urljoin(_PAGE_BASE_URL, pdf_link["href"]) if pdf_link else None,
            }
        )
    return disclosures


def fetch_all_disclosures(target_date: date_cls, max_pages: int = 10) -> list[dict]:
    """指定日のTDnet開示一覧を全件取得する(コード絞り込みなし)。

    1ページ最大100件。値の大きい日(決算発表集中日など)でも取り切れるよう
    max_pagesに余裕を持たせている。
    """
    all_rows: list[dict] = []
    for page in range(1, max_pages + 1):
        html = _fetch_page(page, target_date)
        if html is None:
            break
        rows = _parse_rows(html)
        if not rows:
            break
        all_rows.extend(rows)
        time.sleep(_REQUEST_INTERVAL_SEC)
    return all_rows


def fetch_recent_disclosures(code: str, target_date: date_cls, max_pages: int = 3) -> list[dict]:
    """指定日のTDnet開示一覧から、指定コードに該当する開示のみを返す。"""
    return [r for r in fetch_all_disclosures(target_date, max_pages=max_pages) if r["code"] == code]
