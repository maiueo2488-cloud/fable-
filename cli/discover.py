"""エントリポイント: python -m cli.discover [--date YYYY-MM-DD] [--max-candidates N] [--dry-run]"""

import argparse
import sys
from datetime import date

from jstock.config import load_config
from jstock.discovery.discovery_runner import discover_picks


def _force_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ニュース検知ベースの銘柄発掘(TDnet好材料スキャン)")
    parser.add_argument("--date", type=str, default=None, help="対象日(YYYY-MM-DD、省略時は本日)")
    parser.add_argument("--max-candidates", type=int, default=10, help="検知候補の最大件数")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="J-Quantsへの照会とDiscord送信を省略し、TDnetで検知した候補一覧だけを表示する",
    )
    parser.add_argument(
        "--include-sector-momentum",
        action="store_true",
        help="セクターモメンタムも取得する(無料プランのレート制限に当たりやすいため既定は無効)",
    )
    return parser.parse_args()


def main() -> None:
    _force_utf8_stdio()
    args = parse_args()
    config = load_config()
    target_date = date.fromisoformat(args.date) if args.date else None

    picks = discover_picks(
        config,
        target_date=target_date,
        max_candidates=args.max_candidates,
        dry_run=args.dry_run,
        include_sector_momentum=args.include_sector_momentum,
    )

    print(f"=== 好材料検知 {len(picks)} 件 ===")
    for rank, pick in enumerate(picks, start=1):
        print(f"{rank}. {pick.signal.name} ({pick.signal.code}) [{pick.signal.category}]")
        print(f"   {pick.rationale}")


if __name__ == "__main__":
    main()
