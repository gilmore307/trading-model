from datetime import UTC, datetime

from scripts_set_mode import assert_test_mode_can_start


def test_assert_test_mode_can_start_rejects_when_already_test(monkeypatch):
    monkeypatch.setattr('scripts_set_mode.load_mode_state', lambda: {'mode': 'test'})
    try:
        assert_test_mode_can_start()
    except RuntimeError as exc:
        assert 'already active' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')


def test_assert_test_mode_can_start_rejects_recent_summary(monkeypatch, tmp_path):
    summary = tmp_path / 'latest-test-mode-summary.json'
    summary.write_text('{"generated_at": "%s"}' % datetime.now(UTC).isoformat())
    monkeypatch.setattr('scripts_set_mode.load_mode_state', lambda: {'mode': 'develop'})
    monkeypatch.setattr('scripts_set_mode.TEST_SUMMARY_PATH', summary)
    try:
        assert_test_mode_can_start()
    except RuntimeError as exc:
        assert 'cooldown active' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')
