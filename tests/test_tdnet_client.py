from jstock.news.tdnet_client import _parse_rows

# 2026-06-19分の実ページから採取した構造を模した固定HTML(ライブサイトに依存しない回帰テスト用)
SAMPLE_HTML = """
<table>
<tr>
<td noWrap align="center" class="header-L">時刻</td>
<td noWrap align="center" class="header-M">コード</td>
<td noWrap align="center" class="header-M">会社名</td>
<td noWrap align="center" class="header-M">表題</td>
</tr>
<tr>
<td class="oddnew-L kjTime" noWrap>22:00</td>
<td class="oddnew-M kjCode" noWrap>36590</td>
<td class="oddnew-M kjName" noWrap>ネクソン                  </td>
<td class="oddnew-M kjTitle" align="left"><a href="140120260618573399.pdf" target="_blank">主要株主の異動に関するお知らせ</a></td>
</tr>
<tr>
<td class="evennew-L kjTime" noWrap>20:00</td>
<td class="evennew-M kjCode" noWrap>68970</td>
<td class="evennew-M kjName" noWrap>ツインバード            </td>
<td class="evennew-M kjTitle" align="left"><a href="140120260619575084.pdf" target="_blank">公開買付けの開始予定に関するお知らせ</a></td>
</tr>
</table>
"""


def test_parse_rows_extracts_disclosures_and_skips_header():
    rows = _parse_rows(SAMPLE_HTML)
    assert len(rows) == 2


def test_parse_rows_normalizes_5digit_code_to_4digit():
    rows = _parse_rows(SAMPLE_HTML)
    codes = {r["code"] for r in rows}
    assert codes == {"3659", "6897"}


def test_parse_rows_resolves_relative_pdf_url_to_absolute():
    rows = _parse_rows(SAMPLE_HTML)
    nexon = next(r for r in rows if r["code"] == "3659")
    assert nexon["pdf_url"] == "https://www.release.tdnet.info/inbs/140120260618573399.pdf"
    assert nexon["name"] == "ネクソン"
    assert nexon["title"] == "主要株主の異動に関するお知らせ"
