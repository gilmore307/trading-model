from src.execution.executor import DemoExecutor


class DummyClient:
    account_alias = 'openclaw3'
    account_label = 'OpenClaw3'


def test_submit_entry_signal_persists_account_routing_metadata():
    executor = DemoExecutor(armed=False, client=DummyClient())
    result = executor.submit_entry_signal(
        position_key='meanrev:SOL-USDT-SWAP',
        symbol='SOL/USDT:USDT',
        strategy='meanrev',
        side='long',
        reason='test_signal',
        bar_id=123456,
        order_size_usdt=100.0,
        margin_required_usdt=20.0,
        leverage=5,
        bucket={'available_usdt': 20000.0, 'allocated_usdt': 0.0},
        existing_positions=[],
    )

    position = result.state_patch['positions']['meanrev:SOL-USDT-SWAP'][0]
    event = result.state_patch['history_append'][0]

    assert position['account_alias'] == 'openclaw3'
    assert position['account_label'] == 'OpenClaw3'
    assert event['account_alias'] == 'openclaw3'
    assert event['account_label'] == 'OpenClaw3'
