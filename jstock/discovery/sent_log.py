"""通知済み銘柄の記録(同日内に複数回実行された場合の重複Discord通知を防ぐ)。

1日1回の定期実行を想定しているが、手動実行と被るケースや将来の複数回実行にも
備えて、日付ごとに通知済みコードをファイルへ永続化する。
"""

import json
from datetime import date
from pathlib import Path

DEFAULT_PATH = Path("data/sent_signals.json")


def load_sent_codes(target_date: date, path: Path = DEFAULT_PATH) -> set[str]:
    if not path.exists():
        return set()
    log: dict[str, list[str]] = json.loads(path.read_text(encoding="utf-8"))
    return set(log.get(target_date.isoformat(), []))


def record_sent_codes(target_date: date, codes: list[str], path: Path = DEFAULT_PATH) -> None:
    log: dict[str, list[str]] = {}
    if path.exists():
        log = json.loads(path.read_text(encoding="utf-8"))
    key = target_date.isoformat()
    log[key] = sorted(set(log.get(key, [])) | set(codes))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
