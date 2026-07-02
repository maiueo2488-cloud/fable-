from jstock.news.catalyst_classifier import classify_disclosure, find_positive_candidates


def test_classify_disclosure_detects_upward_revision():
    signal = classify_disclosure(
        {"code": "1000", "name": "テストA", "title": "業績予想の上方修正に関するお知らせ", "pdf_url": "url"}
    )
    assert signal is not None
    assert signal.polarity == "positive"
    assert signal.category == "業績予想の上方修正"
    assert signal.score == 2.5


def test_classify_disclosure_detects_downward_revision():
    signal = classify_disclosure({"code": "1000", "name": "テストA", "title": "業績予想の下方修正に関するお知らせ"})
    assert signal is not None
    assert signal.polarity == "negative"


def test_classify_disclosure_returns_none_for_routine_disclosure():
    signal = classify_disclosure({"code": "1000", "name": "テストA", "title": "役員人事に関するお知らせ"})
    assert signal is None


def test_classify_disclosure_excludes_positive_keyword_with_negation():
    # 実データ検証で発見した誤検知: 「株主優待の見送り」は好材料ではない
    signal = classify_disclosure(
        {"code": "1000", "name": "テストA", "title": "株主優待制度の見送りに関するお知らせ"}
    )
    assert signal is None


def test_classify_disclosure_detects_tob_targeting_own_shares():
    signal = classify_disclosure(
        {
            "code": "6897",
            "name": "ツインバード",
            "title": "株式会社ジャパネットホールディングスによる当社株式に対する公開買付けの開始予定に関するお知らせ",
        }
    )
    assert signal is not None
    assert signal.polarity == "positive"
    assert signal.category == "TOB(買収提案・自社が対象)"


def test_classify_disclosure_excludes_tob_equivalent_shareholding_change():
    # 実データ検証で発見した誤検知: 大株主の株式買い増し(TOBに準ずる行為)は買収提案ではない
    signal = classify_disclosure(
        {
            "code": "3659",
            "name": "ネクソン",
            "title": "主要株主の異動及び当社株式の取得（公開買付けに準ずる行為として政令で定める買集め行為）に関するお知らせ",
        }
    )
    assert signal is None


def test_classify_disclosure_excludes_tendering_into_others_tob():
    # 実データ検証で発見した誤検知: 自社が他社TOBに応募した側は買収対象ではない
    signal = classify_disclosure(
        {"code": "4951", "name": "エステー", "title": "公開買付けへの応募及び特別利益の計上見込に関するお知らせ"}
    )
    assert signal is None


def test_classify_disclosure_sums_score_when_multiple_positive_keywords_match():
    signal = classify_disclosure(
        {"code": "1000", "name": "テストA", "title": "業績予想の上方修正及び増配に関するお知らせ"}
    )
    assert signal is not None
    assert signal.polarity == "positive"
    assert signal.score == 2.5 + 1.5
    assert "業績予想の上方修正" in signal.category
    assert "増配" in signal.category


def test_classify_disclosure_negative_takes_precedence_over_positive():
    # 上方修正(好材料)と特別損失(悪材料)が同時に書かれている場合はリスクを優先する
    signal = classify_disclosure(
        {"code": "1000", "name": "テストA", "title": "通期業績予想の上方修正及び特別損失の計上に関するお知らせ"}
    )
    assert signal is not None
    assert signal.polarity == "negative"
    assert signal.category == "特別損失"


def test_classify_disclosure_excludes_routine_buyback_progress_report():
    # 実データ検証で発見した誤検知: 既存買戻しプログラムの進捗・終了報告はルーティンで新しいニュースではない
    signal = classify_disclosure(
        {"code": "3399", "name": "山岡家", "title": "自己株式の取得状況及び取得終了に関するお知らせ"}
    )
    assert signal is None


def test_classify_disclosure_detects_new_buyback_decision():
    signal = classify_disclosure(
        {"code": "9449", "name": "ＧＭＯ", "title": "自己株式の取得枠設定（300億円）に関するお知らせ"}
    )
    assert signal is not None
    assert signal.polarity == "positive"
    assert signal.category == "自己株式取得(株主還元)"


def test_classify_disclosure_detects_new_categories():
    cases = [
        ("黒字転換に関するお知らせ", "黒字転換"),
        ("株式分割に関するお知らせ", "株式分割"),
        ("子会社化に関するお知らせ", "M&A(当社による買収)"),
        ("製造販売承認に関するお知らせ", "規制当局の承認"),
        ("自己株式の取得に係る取締役会決議に関するお知らせ", "自己株式取得(株主還元)"),
    ]
    for title, expected_category in cases:
        signal = classify_disclosure({"code": "1000", "name": "テストA", "title": title})
        assert signal is not None, title
        assert signal.category == expected_category, title


def test_find_positive_candidates_sorts_by_score_descending():
    disclosures = [
        {"code": "1000", "name": "A社", "title": "株主優待の新設に関するお知らせ"},  # score 1.0
        {"code": "2000", "name": "B社", "title": "黒字転換に関するお知らせ"},  # score 3.0
        {"code": "3000", "name": "C社", "title": "増益に関するお知らせ"},  # score 1.0
    ]
    candidates = find_positive_candidates(disclosures)
    assert [c.code for c in candidates] == ["2000", "1000", "3000"]


def test_find_positive_candidates_dedupes_keeping_highest_score():
    disclosures = [
        {"code": "1000", "name": "A社", "title": "株主優待の新設に関するお知らせ"},  # score 1.0
        {"code": "1000", "name": "A社", "title": "黒字転換に関するお知らせ"},  # score 3.0(同一銘柄でより重要)
    ]
    candidates = find_positive_candidates(disclosures)
    assert len(candidates) == 1
    assert candidates[0].category == "黒字転換"


def test_find_positive_candidates_excludes_negative():
    disclosures = [
        {"code": "1000", "name": "A社", "title": "業績予想の上方修正に関するお知らせ"},
        {"code": "2000", "name": "B社", "title": "業績予想の下方修正に関するお知らせ"},
        {"code": "4000", "name": "D社", "title": "役員人事に関するお知らせ"},
    ]
    candidates = find_positive_candidates(disclosures)
    assert [c.code for c in candidates] == ["1000"]
