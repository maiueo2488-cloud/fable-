"""適時開示からカタリスト確認情報を組み立てる(純粋関数)。"""

from jstock.types import NewsConfirmation


def build_news_confirmation(code: str, disclosures: list[dict]) -> NewsConfirmation:
    headlines = tuple(d["title"] for d in disclosures if d.get("title"))
    if not headlines:
        return NewsConfirmation(code=code, headlines=(), catalyst_summary="直近の適時開示なし")

    summary = "直近の開示: " + " / ".join(headlines[:3])
    return NewsConfirmation(code=code, headlines=headlines, catalyst_summary=summary)
