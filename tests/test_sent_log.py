from datetime import date
from pathlib import Path

from jstock.discovery.sent_log import load_sent_codes, record_sent_codes


def test_load_sent_codes_returns_empty_set_when_file_missing(tmp_path: Path):
    path = tmp_path / "sent.json"
    assert load_sent_codes(date(2026, 6, 19), path=path) == set()


def test_record_then_load_roundtrip(tmp_path: Path):
    path = tmp_path / "sent.json"
    record_sent_codes(date(2026, 6, 19), ["6897", "3544"], path=path)

    assert load_sent_codes(date(2026, 6, 19), path=path) == {"6897", "3544"}


def test_record_sent_codes_merges_with_existing_and_keeps_other_dates_separate(tmp_path: Path):
    path = tmp_path / "sent.json"
    record_sent_codes(date(2026, 6, 19), ["6897"], path=path)
    record_sent_codes(date(2026, 6, 19), ["3544"], path=path)
    record_sent_codes(date(2026, 6, 20), ["9999"], path=path)

    assert load_sent_codes(date(2026, 6, 19), path=path) == {"6897", "3544"}
    assert load_sent_codes(date(2026, 6, 20), path=path) == {"9999"}
