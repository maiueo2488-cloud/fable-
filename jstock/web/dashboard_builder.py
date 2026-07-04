"""セクター資金フロー(近似指標)ダッシュボードの静的HTML生成。

sector_momentum.py が算出する momentum_score(株価リターン+出来高変化ベースの
資金フロー近似指標)を、東証33業種の diverging bar chart + テーブルとして
1枚の自己完結HTMLにレンダリングする。外部CDN・JS依存なし(GitHub Pages等での
オフライン表示を想定)。
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from jstock.config import Config
from jstock.runner import _FREE_PLAN_DELAY_DAYS, fetch_sector_momentum_map
from jstock.types import SectorMomentum


def _format_pct(value: float) -> str:
    return f"{value * 100:+.1f}%"


def _bar_geometry(score: float, max_abs: float) -> tuple[float, float, str]:
    """中央(50%)を基準とするdivergingバーの (left%, width%, side) を返す。"""
    if max_abs <= 0:
        return 50.0, 0.0, "flat"
    half = min(abs(score) / max_abs, 1.0) * 50.0
    if score >= 0:
        return 50.0, half, "positive"
    return 50.0 - half, half, "negative"


def _sector_row_html(rank: int, m: SectorMomentum, max_abs: float, labeled: bool) -> str:
    left, width, side = _bar_geometry(m.momentum_score, max_abs)
    tip_label = f'<span class="tip {side}">{m.momentum_score:+.3f}</span>' if labeled else ""
    tooltip = (
        f"{m.sector}: 1週{_format_pct(m.return_1w)} / 1ヶ月{_format_pct(m.return_1m)} "
        f"/ 出来高比{m.volume_ratio:.2f} / momentum_score {m.momentum_score:+.3f}"
    )
    return f"""      <div class="row" title="{tooltip}">
        <div class="rank">{rank}</div>
        <div class="name">{m.sector}</div>
        <div class="track">
          <div class="baseline"></div>
          <div class="bar {side}" style="left:{left:.2f}%;width:{width:.2f}%"></div>
        </div>
        <div class="tip-slot">{tip_label}</div>
      </div>"""


def _table_row_html(m: SectorMomentum) -> str:
    return f"""            <tr>
              <td>{m.sector}</td>
              <td class="num">{_format_pct(m.return_1w)}</td>
              <td class="num">{_format_pct(m.return_1m)}</td>
              <td class="num">{m.volume_ratio:.2f}</td>
              <td class="num">{m.momentum_score:+.3f}</td>
            </tr>"""


_CSS = """
  .viz-root {
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --text-muted: #898781;
    --gridline: #e1e0d9;
    --baseline: #c3c2b7;
    --pos: #2a78d6;
    --neg: #e34948;
    --neutral: #f0efec;
    --border: rgba(11,11,11,0.10);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    background: var(--page);
    color: var(--text-primary);
    max-width: 860px;
    margin: 0 auto;
    padding: 32px 20px 64px;
  }
  @media (prefers-color-scheme: dark) {
    .viz-root {
      --surface-1: #1a1a19;
      --page: #0d0d0d;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --text-muted: #898781;
      --gridline: #2c2c2a;
      --baseline: #383835;
      --pos: #3987e5;
      --neg: #e66767;
      --neutral: #383835;
      --border: rgba(255,255,255,0.10);
    }
  }
  .viz-root h1 { font-size: 20px; margin: 0 0 4px; }
  .viz-root .subtitle { color: var(--text-secondary); font-size: 13px; margin: 0 0 12px; }
  .viz-root .disclaimer {
    color: var(--text-secondary); font-size: 12.5px; line-height: 1.6;
    background: var(--surface-1); border: 1px solid var(--border);
    border-radius: 8px; padding: 10px 14px; margin: 0 0 20px;
  }
  .viz-root .legend { display: flex; align-items: center; gap: 8px 20px; flex-wrap: wrap; font-size: 12.5px; color: var(--text-secondary); margin: 0 0 16px; }
  .viz-root .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
  .viz-root .swatch.positive { background: var(--pos); }
  .viz-root .swatch.negative { background: var(--neg); }
  .viz-root .chart { background: var(--surface-1); border: 1px solid var(--border); border-radius: 10px; padding: 8px 16px; }
  .viz-root .row { display: grid; grid-template-columns: 28px 108px 1fr 64px; align-items: center; gap: 10px; padding: 2px 0; border-bottom: 1px solid var(--gridline); }
  .viz-root .row:last-child { border-bottom: none; }
  .viz-root .rank { color: var(--text-muted); font-size: 11px; text-align: right; font-variant-numeric: tabular-nums; }
  .viz-root .name { font-size: 12.5px; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .viz-root .track { position: relative; height: 20px; }
  .viz-root .track .baseline { position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: var(--baseline); }
  .viz-root .track .bar { position: absolute; top: 2px; height: 16px; }
  .viz-root .track .bar.positive { background: var(--pos); border-radius: 0 4px 4px 0; }
  .viz-root .track .bar.negative { background: var(--neg); border-radius: 4px 0 0 4px; }
  .viz-root .tip-slot { font-size: 11px; font-variant-numeric: tabular-nums; text-align: right; }
  .viz-root .tip { color: var(--text-secondary); }
  .viz-root .empty { color: var(--text-secondary); font-size: 13px; }
  .viz-root .data-table { width: 100%; border-collapse: collapse; margin-top: 28px; font-size: 12.5px; }
  .viz-root .data-table caption { text-align: left; color: var(--text-secondary); font-size: 12.5px; margin-bottom: 8px; }
  .viz-root .data-table th, .viz-root .data-table td { padding: 6px 10px; border-bottom: 1px solid var(--gridline); text-align: left; }
  .viz-root .data-table th { color: var(--text-muted); font-weight: 600; }
  .viz-root .data-table td.num, .viz-root .data-table th.num { text-align: right; font-variant-numeric: tabular-nums; }
"""


def render_dashboard_html(
    momentum: list[SectorMomentum],
    as_of: date,
    generated_at: date | None = None,
) -> str:
    """momentum(順不同で可、内部でmomentum_score降順に並べ替える)から自己完結HTMLを生成する。"""
    ranked = sorted(momentum, key=lambda m: m.momentum_score, reverse=True)
    generated_at = generated_at or date.today()

    if not ranked:
        chart_html = '<p class="empty">データを取得できませんでした(J-Quants APIキー未設定、または対象期間のデータが取得できませんでした)。</p>'
        table_html = ""
    else:
        max_abs = max(abs(m.momentum_score) for m in ranked) or 1.0
        extreme_sectors = {m.sector for m in ranked[:3]} | {m.sector for m in ranked[-3:]}
        rows = "\n".join(
            _sector_row_html(i + 1, m, max_abs, m.sector in extreme_sectors) for i, m in enumerate(ranked)
        )
        chart_html = f'<div class="chart">\n{rows}\n      </div>'
        table_rows = "\n".join(_table_row_html(m) for m in ranked)
        table_html = f"""
    <table class="data-table">
      <caption>全{len(ranked)}業種の内訳(J-Quants業種区分S33Nmベース)</caption>
      <thead>
        <tr>
          <th>業種</th><th class="num">1週リターン</th><th class="num">1ヶ月リターン</th>
          <th class="num">出来高比</th><th class="num">momentum_score</th>
        </tr>
      </thead>
      <tbody>
{table_rows}
      </tbody>
    </table>"""

    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>日本株セクター資金フロー(近似指標)ダッシュボード</title>
<style>{_CSS}</style>
</head>
<body>
  <main class="viz-root">
    <h1>日本株セクター資金フロー(近似指標)ダッシュボード</h1>
    <p class="subtitle">データ基準日(目安): {as_of.isoformat()} ／ 生成日: {generated_at.isoformat()}</p>
    <p class="disclaimer">
      J-Quants無料プランを使用しているため、市場データは実際の取引日から約12週間遅延しています。
      また「海外投資家動向」「信用残高」は無料プランでは取得できないため、ここでの資金フローは
      <strong>株価リターン+出来高変化から算出した近似指標(momentum_score)</strong>です。
      実際の売買判断の根拠には使わず、業種間の傾向把握の参考情報としてご利用ください。
    </p>
    <div class="legend">
      <span><span class="swatch positive"></span>momentum上昇(資金流入寄り)</span>
      <span><span class="swatch negative"></span>momentum低下(資金流出寄り)</span>
    </div>
    {chart_html}
    {table_html}
  </main>
</body>
</html>
"""


def build_dashboard(config: Config, output_path: Path = Path("docs/index.html")) -> None:
    """セクターモメンタムを取得し、静的HTMLダッシュボードを output_path に書き出す。

    J-Quants APIキー未設定時は fetch_sector_momentum_map が空dictを返すため、
    その場合も「データなし」表示のHTMLとして正常終了する。
    """
    momentum_map = fetch_sector_momentum_map(config)
    as_of = date.today() - timedelta(days=_FREE_PLAN_DELAY_DAYS)
    html = render_dashboard_html(list(momentum_map.values()), as_of=as_of)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
