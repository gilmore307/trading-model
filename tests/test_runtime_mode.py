from datetime import UTC, datetime

from src.runtime_mode import default_mode


def test_default_mode_is_review_during_sunday_midnight_beijing_window():
    now_utc = datetime(2026, 3, 7, 16, 5, tzinfo=UTC)  # 2026-03-08 00:05 Asia/Shanghai
    assert default_mode(now_utc) == 'review'


def test_default_mode_is_develop_outside_review_window():
    now_utc = datetime(2026, 3, 10, 4, 0, tzinfo=UTC)
    assert default_mode(now_utc) == 'develop'
