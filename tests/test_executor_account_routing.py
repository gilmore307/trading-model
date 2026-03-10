from src.execution.executor import DemoExecutor, realized_pnl_from_prices
from src.risk.manager import RiskManager
from src.review.review_runner import build_fee_analysis, filter_prod_state, summarize_history
from src.storage.state import StateStore


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


def test_realized_pnl_from_prices_supports_long_and_short():
    assert realized_pnl_from_prices('long', 2.0, 100.0, 110.0) == 20.0
    assert realized_pnl_from_prices('short', 2.0, 100.0, 90.0) == 20.0
    assert realized_pnl_from_prices('long', 2.0, 100.0, 90.0) == -20.0



def test_submit_entry_signal_rolls_fee_into_bucket_totals():
    class FeeClient(DummyClient):
        def create_entry_order(self, *args, **kwargs):
            return {
                'order_id': 'o1',
                'status': 'filled',
                'order_side': 'buy',
                'ccxt_symbol': 'SOL/USDT:USDT',
                'notional_usdt': 100.0,
                'amount': 2.0,
                'reference_price': 50.0,
                'fee_usdt': 0.75,
                'fee_ccy': ['USDT'],
                'fee_rate': ['0.001'],
                'fill_ids': ['f1'],
                'fill_count': 1,
                'verified_entry': True,
                'live_contracts': 2.0,
                'live_side': 'long',
                'verification_attempts': [],
            }

    executor = DemoExecutor(armed=True, client=FeeClient())
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
        bucket={'available_usdt': 20000.0, 'allocated_usdt': 0.0, 'fees_usdt': None},
        existing_positions=[],
    )

    bucket = result.state_patch['buckets']['meanrev:SOL-USDT-SWAP']
    assert bucket['fees_usdt'] == 0.75



def test_submit_exit_signal_rolls_fee_into_bucket_totals():
    class FeeClient(DummyClient):
        def create_exit_order(self, *args, **kwargs):
            return {
                'order_id': 'o2',
                'status': 'filled',
                'order_side': 'sell',
                'ccxt_symbol': 'SOL/USDT:USDT',
                'requested_amount': 2.0,
                'amount': 2.0,
                'reference_price': 55.0,
                'fee_usdt': 0.25,
                'fee_ccy': ['USDT'],
                'fee_rate': ['0.001'],
                'fill_ids': ['f2'],
                'fill_count': 1,
                'verified_flat': True,
                'remaining_contracts': 0.0,
                'remaining_side': None,
                'verification_attempts': [],
                'order_attempts': [],
            }

    executor = DemoExecutor(armed=True, client=FeeClient())
    positions = [{'status': 'open', 'side': 'long', 'amount': 2.0, 'margin_required_usdt': 20.0, 'notional_usdt': 100.0, 'trade_id': 't1', 'reference_price': 50.0}]
    result = executor.submit_exit_signal(
        position_key='meanrev:SOL-USDT-SWAP',
        symbol='SOL/USDT:USDT',
        strategy='meanrev',
        positions=positions,
        reason='flat_signal',
        bar_id=123457,
        bucket={'available_usdt': 19980.0, 'allocated_usdt': 20.0, 'fees_usdt': 0.75},
        exit_side=None,
    )

    bucket = result.state_patch['buckets']['meanrev:SOL-USDT-SWAP']
    assert bucket['fees_usdt'] == 1.0
    assert bucket['realized_pnl_usdt'] == 10.0
    position = result.state_patch['positions']['meanrev:SOL-USDT-SWAP'][0]
    assert position['realized_pnl_usdt'] == 10.0
    event = result.state_patch['history_append'][0]
    assert event['realized_pnl_usdt'] == 10.0



def test_state_store_normalizes_none_bucket_fee_fields(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{"buckets":{"breakout:BTC-USDT-SWAP":{"initial_capital_usdt":20000,"available_usdt":20000,"allocated_usdt":0,"fees_usdt":null,"realized_pnl_usdt":null}}}')
    state = StateStore(path).load()
    bucket = state['buckets']['breakout:BTC-USDT-SWAP']
    assert bucket['fees_usdt'] == 0.0
    assert bucket['realized_pnl_usdt'] == 0.0



def test_state_store_backfills_closed_position_realized_pnl(tmp_path):
    path = tmp_path / 'state.json'
    path.write_text('{"positions":{"breakout:BTC-USDT-SWAP":[{"status":"closed","side":"long","amount":2,"reference_price":100,"exit_reference_price":110}]},"buckets":{"breakout:BTC-USDT-SWAP":{"initial_capital_usdt":20000,"available_usdt":20000,"allocated_usdt":0,"fees_usdt":0,"realized_pnl_usdt":null}}}')
    state = StateStore(path).load()
    position = state['positions']['breakout:BTC-USDT-SWAP'][0]
    bucket = state['buckets']['breakout:BTC-USDT-SWAP']
    assert position['realized_pnl_usdt'] == 20.0
    assert bucket['realized_pnl_usdt'] == 20.0



def test_risk_manager_tolerates_none_bucket_fee_fields():
    bucket = {'initial_capital_usdt': 20000.0, 'available_usdt': 20000.0, 'allocated_usdt': 0.0, 'fees_usdt': None, 'realized_pnl_usdt': None}
    assert RiskManager().bucket_equity_usdt(bucket) == 20000.0



def test_review_fee_coverage_counts_only_execution_events():
    state = {
        'history': [
            {'event_id': 'e1', 'type': 'entry', 'strategy': 'breakout', 'symbol': 'BTC-USDT-SWAP', 'bar_id': 1, 'fee_usdt': 0.1},
            {'event_id': 'e2', 'type': 'exit', 'strategy': 'breakout', 'symbol': 'BTC-USDT-SWAP', 'bar_id': 2, 'fee_usdt': None, 'exit_fee_usdt': None, 'realized_pnl_usdt': 3.5},
            {'event_id': 'e3', 'type': 'bucket_lock', 'strategy': 'breakout', 'symbol': 'BTC-USDT-SWAP', 'bar_id': 3},
            {'event_id': 'e4', 'type': 'reconcile_mismatch', 'strategy': 'breakout', 'symbol': 'BTC-USDT-SWAP', 'bar_id': 4},
        ]
    }
    summary = summarize_history(state)
    assert summary['fees']['expected_fee_events'] == 2
    assert summary['fees']['events_with_fee'] == 1
    assert summary['fees']['events_missing_fee'] == 1
    assert summary['fees']['fee_coverage_ratio'] == 0.5
    assert summary['fees']['missing_fee_event_ids'] == ['e2']
    assert summary['realized_pnl_usdt_total'] == 3.5



def test_fee_analysis_recommends_reduce_frequency_when_fee_burden_is_high():
    summary = {
        'fees': {
            'expected_fee_events': 10,
            'events_with_fee': 10,
            'events_missing_fee': 0,
            'fee_usdt_total': 30.0,
            'fee_coverage_ratio': 1.0,
        },
        'realized_pnl_usdt_total': 100.0,
    }
    state = {'buckets': {}}
    analysis = build_fee_analysis(summary, state)
    assert analysis['fee_to_realized_pnl_ratio'] == 0.3
    assert analysis['frequency_adjustment_recommendation'] == 'reduce_frequency'



def test_fee_analysis_keeps_frequency_when_fee_burden_is_low():
    summary = {
        'fees': {
            'expected_fee_events': 10,
            'events_with_fee': 10,
            'events_missing_fee': 0,
            'fee_usdt_total': 5.0,
            'fee_coverage_ratio': 1.0,
        },
        'realized_pnl_usdt_total': 100.0,
    }
    state = {'buckets': {}}
    analysis = build_fee_analysis(summary, state)
    assert analysis['fee_to_realized_pnl_ratio'] == 0.05
    assert analysis['frequency_adjustment_recommendation'] == 'no_change'



def test_filter_prod_state_excludes_test_positions_buckets_and_history():
    state = {
        'positions': {
            'breakout:BTC-USDT-SWAP': [{'status': 'open'}],
            'test:breakout:XRP-USDT-SWAP': [{'status': 'open'}],
        },
        'buckets': {
            'breakout:BTC-USDT-SWAP': {'initial_capital_usdt': 1},
            'test:breakout:XRP-USDT-SWAP': {'initial_capital_usdt': 1},
        },
        'last_signals': {
            'breakout:BTC-USDT-SWAP': {'side': 'long'},
            'test:breakout:XRP-USDT-SWAP': {'side': 'long'},
        },
        'history': [
            {'position_key': 'breakout:BTC-USDT-SWAP', 'strategy': 'breakout', 'type': 'entry'},
            {'position_key': 'test:breakout:XRP-USDT-SWAP', 'strategy': 'test_breakout', 'type': 'entry'},
        ],
        'open_positions': 2,
    }
    filtered = filter_prod_state(state)
    assert set(filtered['positions']) == {'breakout:BTC-USDT-SWAP'}
    assert set(filtered['buckets']) == {'breakout:BTC-USDT-SWAP'}
    assert set(filtered['last_signals']) == {'breakout:BTC-USDT-SWAP'}
    assert len(filtered['history']) == 1
    assert filtered['open_positions'] == 1



def test_fee_analysis_marks_insufficient_profit_basis_when_profit_not_positive():
    summary = {
        'fees': {
            'expected_fee_events': 4,
            'events_with_fee': 4,
            'events_missing_fee': 0,
            'fee_usdt_total': 2.0,
            'fee_coverage_ratio': 1.0,
        }
    }
    state = {
        'buckets': {
            'breakout:BTC-USDT-SWAP': {'realized_pnl_usdt': 0.0},
        }
    }
    analysis = build_fee_analysis(summary, state)
    assert analysis['fee_to_realized_pnl_ratio'] is None
    assert analysis['frequency_adjustment_recommendation'] == 'insufficient_profit_basis'
