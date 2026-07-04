"""エントリポイント: python -m cli.build_dashboard [--output PATH]"""

import argparse
import sys
from pathlib import Path

from jstock.config import load_config
from jstock.web.dashboard_builder import build_dashboard


def _force_utf8_stdio() -> None:
    """Windows環境でのコンソール文字コード起因の文字化けを防ぐ。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="セクター資金フロー(近似指標)ダッシュボードの静的HTML生成")
    parser.add_argument("--output", type=Path, default=Path("docs/index.html"), help="出力先HTMLファイルパス")
    return parser.parse_args()


def main() -> None:
    _force_utf8_stdio()
    args = parse_args()
    config = load_config()
    build_dashboard(config, output_path=args.output)
    print(f"ダッシュボードを生成しました: {args.output}")


if __name__ == "__main__":
    main()
