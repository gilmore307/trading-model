from src.runtime_guards import assert_single_okx_trading_daemon_context


def test_assert_single_okx_trading_daemon_context_passes_when_no_matches(monkeypatch):
    monkeypatch.setattr('src.runtime_guards.list_okx_trading_daemon_pids', lambda: [])
    assert_single_okx_trading_daemon_context()


def test_assert_single_okx_trading_daemon_context_raises_on_conflict(monkeypatch):
    monkeypatch.setattr('src.runtime_guards.list_okx_trading_daemon_pids', lambda: [
        {'pid': 12345, 'cwd': '/root/.openclaw/workspace/projects/okx-trading', 'cmdline': 'bash ./run_daemon.sh'}
    ])
    try:
        assert_single_okx_trading_daemon_context()
    except RuntimeError as exc:
        assert 'conflicting_okx_trading_daemon_instances_detected' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')


def test_assert_single_okx_trading_daemon_context_can_allow_current_pid(monkeypatch):
    monkeypatch.setattr('src.runtime_guards.list_okx_trading_daemon_pids', lambda: [
        {'pid': 12345, 'cwd': '/root/.openclaw/workspace/projects/okx-trading', 'cmdline': 'bash ./run_daemon.sh'}
    ])
    assert_single_okx_trading_daemon_context(allow_current_run_daemon_pid=12345)
