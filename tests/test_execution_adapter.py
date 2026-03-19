from src.execution.adapters import DryRunExecutionAdapter


def test_dry_run_execution_adapter_returns_receipt_for_entry_and_exit():
    adapter = DryRunExecutionAdapter()
    entry = adapter.submit_entry(account='trend', symbol='BTC-USDT-SWAP', side='long', size=1.0, reason='test')
    exit_ = adapter.submit_exit(account='trend', symbol='BTC-USDT-SWAP', reason='test')
    assert entry.accepted is True
    assert entry.mode == 'dry_run'
    assert entry.order_id == 'dry-run-entry'
    assert entry.execution_id is not None
    assert entry.client_order_id is not None
    assert entry.trade_ids == []
    assert exit_.accepted is True
    assert exit_.order_id == 'dry-run-exit'
    assert exit_.execution_id is not None
    assert exit_.client_order_id is not None
    assert exit_.trade_ids == []
