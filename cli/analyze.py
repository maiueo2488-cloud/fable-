"""エントリポイント: python -m cli.analyze [--shikiho-path PATH] [--top-n N] [--dry-run]"""

import argparse
import sys
from dataclasses import replace
from pathlib import Path

from jstock.config import load_config
from jstock.runner import run_analysis


def _force_utf8_stdio() -> None:
    """Windows環境でのコンソール文字コード起因の文字化けを防ぐ。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="日本株 銘柄発掘 & Discord通知")
    parser.add_argument(
        "--shikiho-path",
        type=Path,
        default=None,
        help="四季報データファイルのパス(省略時は.envのSHIKIHO_DATA_PATH)",
    )
    parser.add_argument("--top-n", type=int, default=20, help="スコア上位何件を対象にするか")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="J-Quants/TDnetへの外部通信とDiscord送信を省略し、ローカルスコアランキングのみ表示する",
    )
    return parser.parse_args()


def main() -> None:
    _force_utf8_stdio()
    args = parse_args()
    config = load_config()
    if args.shikiho_path is not None:
        config = replace(config, shikiho_data_path=args.shikiho_path)

    picks = run_analysis(config, top_n=args.top_n, dry_run=args.dry_run)

    print(f"=== スコア上位 {len(picks)} 件 ===")
    for rank, pick in enumerate(picks, start=1):
        print(f"{rank}. {pick.record.name} ({pick.record.code}) score={pick.score.total_score:.3f}")
        print(f"   {pick.rationale}")


if __name__ == "__main__":
    main()
