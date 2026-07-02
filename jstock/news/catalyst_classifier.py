"""TDnet開示の見出しから好材料/悪材料を分類し、重要度でスコアリングする(純粋関数)。

四季報のような網羅的なファンダメンタルズファイルが無くても、開示の見出しに含まれる
定型キーワードから「株価が動きそうな銘柄」を一次検知するためのヒューリスティクス。
1件の開示に複数の要因が含まれる場合はスコアを合算し、株価インパクトが大きいと
見込まれる項目を優先して「厳選」できるようにする。キーワードと重みは初版であり、
loopでの継続的な調整を前提とする。
"""

from jstock.types import CatalystSignal

# キーワード -> (カテゴリ名, 重み)。重みは株価インパクトの目安(3.0=非常に大きい〜1.0=小さい)。
# 1件の開示に複数該当した場合はスコアを合算し、カテゴリ名は「・」で連結する。
_POSITIVE_KEYWORDS: dict[str, tuple[str, float]] = {
    # 「に対する公開買付け」は「[買収者]による[当社]株式に対する公開買付け」という
    # 自社が買収対象になるケースのみを捉えるための表現。単に「公開買付け」だと、
    # 「公開買付けに準ずる行為」(大株主の株式買い増し等)や「公開買付けへの応募」
    # (自社が他社TOBに応募した側)も誤って好材料に分類してしまうため絞っている。
    "に対する公開買付け": ("TOB(買収提案・自社が対象)", 3.0),
    "黒字化": ("黒字転換", 3.0),
    "黒字転換": ("黒字転換", 3.0),
    "上方修正": ("業績予想の上方修正", 2.5),
    "最高益": ("最高益更新", 2.5),
    "増収増益": ("増収増益", 2.0),
    "子会社化": ("M&A(当社による買収)", 2.0),
    "株式分割": ("株式分割", 1.5),
    "資本提携": ("資本提携", 1.5),
    "特別配当": ("特別配当", 1.5),
    "増配": ("増配", 1.5),
    "大型契約": ("大型受注・契約", 1.5),
    "受注獲得": ("大型受注・契約", 1.5),
    "薬事承認": ("規制当局の承認", 2.0),
    "製造販売承認": ("規制当局の承認", 2.0),
    "増益": ("増益", 1.0),
    "業務提携": ("業務提携", 1.0),
    "自己株式の取得": ("自己株式取得(株主還元)", 1.5),
    "株主優待": ("株主優待の新設・拡充", 1.0),
    "新製品": ("新製品・新サービス", 1.0),
    "特許": ("特許取得", 0.5),
}

_NEGATIVE_KEYWORDS: dict[str, tuple[str, float]] = {
    "民事再生": ("経営破綻", 3.0),
    "破産": ("経営破綻", 3.0),
    "不適正": ("不正会計・コンプライアンス問題", 3.0),
    "不正": ("不正会計・コンプライアンス問題", 3.0),
    "上場廃止": ("上場廃止", 3.0),
    "赤字転落": ("赤字転落", 2.5),
    "下方修正": ("業績予想の下方修正", 2.5),
    "行政処分": ("行政処分", 2.5),
    "課徴金": ("行政処分", 2.5),
    "特別損失": ("特別損失", 2.0),
    "第三者割当": ("第三者割当増資(希薄化懸念)", 1.5),
    "減益": ("減益", 1.5),
    "減配": ("減配", 1.5),
    "無配": ("無配", 1.5),
}

# 好材料キーワードを否定・無効化する語。実データ検証で見つかった誤検知の対処:
# - 「見送り」等: 「株主優待の見送り」のように好材料を否定する文脈
# - 「取得状況」「取得終了」: 既存の自己株式買戻しプログラムの進捗・終了報告(ルーティン)。
#   新規の買戻し決定(取得枠設定・取締役会決議)とは異なり、新しいニュースではないため除外する。
_NEGATION_PHRASES = ("見送り", "中止", "取りやめ", "撤回", "延期", "取得状況", "取得終了")


def _match_all(title: str, keywords: dict[str, tuple[str, float]]) -> list[tuple[str, float]]:
    return [info for keyword, info in keywords.items() if keyword in title]


def classify_disclosure(disclosure: dict) -> CatalystSignal | None:
    """1件のTDnet開示を好材料/悪材料に分類する。該当なしならNone。

    複数キーワードに該当する場合はスコアを合算し、カテゴリ名を連結する。
    ネガティブキーワードが1つでも該当する場合は、ネガティブを優先する
    (好材料との混在時にリスクを見落とさないため)。
    """
    title = disclosure.get("title", "")
    negative_matches = _match_all(title, _NEGATIVE_KEYWORDS)
    if negative_matches:
        return _build_signal(disclosure, title, negative_matches, polarity="negative")

    if any(phrase in title for phrase in _NEGATION_PHRASES):
        return None

    positive_matches = _match_all(title, _POSITIVE_KEYWORDS)
    if positive_matches:
        return _build_signal(disclosure, title, positive_matches, polarity="positive")

    return None


def _build_signal(
    disclosure: dict, title: str, matches: list[tuple[str, float]], polarity: str
) -> CatalystSignal:
    total_score = sum(weight for _, weight in matches)
    categories = "・".join(dict.fromkeys(category for category, _ in matches))
    return CatalystSignal(
        code=disclosure["code"],
        name=disclosure.get("name", ""),
        title=title,
        category=categories,
        polarity=polarity,
        score=total_score,
        pdf_url=disclosure.get("pdf_url"),
    )


def find_positive_candidates(disclosures: list[dict]) -> list[CatalystSignal]:
    """好材料に分類された開示を、スコアが高い順に厳選して返す(同一銘柄は最高スコアの1件のみ)。"""
    signals = (classify_disclosure(d) for d in disclosures)
    positives = [s for s in signals if s is not None and s.polarity == "positive"]
    positives.sort(key=lambda s: s.score, reverse=True)

    seen_codes: set[str] = set()
    candidates: list[CatalystSignal] = []
    for signal in positives:
        if signal.code in seen_codes:
            continue
        seen_codes.add(signal.code)
        candidates.append(signal)
    return candidates
