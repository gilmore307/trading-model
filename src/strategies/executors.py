from __future__ import annotations

from dataclasses import dataclass, field

from src.config.settings import Settings
from src.runners.regime_runner import RegimeRunnerOutput


@dataclass(slots=True)
class ExecutionPlan:
    regime: str
    account: str | None
    action: str
    side: str | None = None
    size: float | None = None
    reason: str | None = None
    score: float | None = None
    blockers: list[str] = field(default_factory=list)
    signals: dict = field(default_factory=dict)
    subscores: dict[str, float] = field(default_factory=dict)


class BaseExecutor:
    regime: str = 'unknown'

    def settings(self, output: RegimeRunnerOutput) -> Settings:
        return output.settings or Settings.load()

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        raise NotImplementedError


class TrendExecutor(BaseExecutor):
    regime = 'trend'

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        cfg = self.settings(output)
        account = output.route_decision['account']
        bg_adx = float(output.background_features.get('adx') or 0.0)
        bg_slope20 = float(output.background_features.get('ema20_slope') or 0.0)
        bg_slope50 = float(output.background_features.get('ema50_slope') or 0.0)
        p_adx = float(output.primary_features.get('adx') or 0.0)
        p_z = float(output.primary_features.get('vwap_deviation_z') or 0.0)
        p_bw = float(output.primary_features.get('bollinger_bandwidth_pct') or 0.0)
        e_z = float(output.override_features.get('vwap_deviation_z') or 0.0)
        trade_burst = float(output.override_features.get('trade_burst_score') or 0.0)

        aligned = bg_slope20 * bg_slope50 > 0
        side = 'long' if bg_slope20 >= 0 else 'short'
        stretched = abs(p_z) >= 2.2 and abs(e_z) >= 1.8
        compressed_pause = p_bw <= 0.015 and trade_burst < cfg.trend_trade_burst_min

        follow_through = 0.0
        subscores = {
            'bg_regime_strength': 1.0 if bg_adx >= cfg.trend_bg_adx_min else 0.0,
            'bg_alignment': 1.0 if aligned else 0.0,
            'primary_adx_confirmation': 1.0 if p_adx >= cfg.trend_primary_adx_min else 0.0,
            'primary_extension_confirmation': 1.0 if abs(p_z) >= 0.6 else 0.0,
            'override_extension_confirmation': 1.0 if abs(e_z) >= 0.8 else 0.0,
            'trade_burst_confirmation': 1.0 if trade_burst >= cfg.trend_trade_burst_min else 0.0,
            'stretch_penalty': -1.0 if stretched else 0.0,
            'compression_pause_penalty': -1.0 if compressed_pause else 0.0,
        }
        if subscores['primary_adx_confirmation']:
            follow_through += 1.0
        if subscores['primary_extension_confirmation']:
            follow_through += 1.0
        if subscores['override_extension_confirmation']:
            follow_through += 1.0
        if subscores['trade_burst_confirmation']:
            follow_through += 1.0

        blockers: list[str] = []
        if bg_adx < cfg.trend_bg_adx_min:
            blockers.append('bg_adx_below_threshold')
        if not aligned:
            blockers.append('background_slopes_not_aligned')
        if stretched:
            blockers.append('overextended_trend')
        if compressed_pause:
            blockers.append('compressed_pause')

        signals = {
            'bg_adx': bg_adx,
            'bg_slope20': bg_slope20,
            'bg_slope50': bg_slope50,
            'p_adx': p_adx,
            'p_z': p_z,
            'p_bw': p_bw,
            'e_z': e_z,
            'trade_burst': trade_burst,
            'aligned': aligned,
            'stretched': stretched,
            'compressed_pause': compressed_pause,
        }

        if bg_adx >= cfg.trend_bg_adx_min and aligned:
            if follow_through >= cfg.trend_follow_through_enter_min and not stretched:
                return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='trend_follow_through_confirmed', score=follow_through, blockers=blockers, signals=signals, subscores=subscores)
            if follow_through >= cfg.trend_follow_through_arm_min and not compressed_pause:
                return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='trend_setup_arming', score=follow_through, blockers=blockers, signals=signals, subscores=subscores)

        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='trend_wait_or_overextended', score=follow_through, blockers=blockers, signals=signals, subscores=subscores)


class RangeExecutor(BaseExecutor):
    regime = 'range'

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        cfg = self.settings(output)
        account = output.route_decision['account']
        p_adx = float(output.primary_features.get('adx') or 0.0)
        p_z = float(output.primary_features.get('vwap_deviation_z') or 0.0)
        p_bw = float(output.primary_features.get('bollinger_bandwidth_pct') or 0.0)
        e_z = float(output.override_features.get('vwap_deviation_z') or 0.0)
        trade_burst = float(output.override_features.get('trade_burst_score') or 0.0)
        bg_adx = float(output.background_features.get('adx') or 0.0)
        bg_slope20 = float(output.background_features.get('ema20_slope') or 0.0)
        bg_slope50 = float(output.background_features.get('ema50_slope') or 0.0)

        side = 'short' if p_z >= 0 else 'long'
        trend_pressure = bg_adx >= cfg.trend_bg_adx_min and bg_slope20 * bg_slope50 > 0 and abs(bg_slope20) > 0.5
        bursty = trade_burst >= cfg.range_trade_burst_max or abs(e_z) >= 1.8
        bandwidth_in_range = 0.08 <= p_bw <= 0.30

        reversion_score = 0.0
        subscores = {
            'low_adx_confirmation': 1.0 if p_adx <= cfg.range_primary_adx_max else 0.0,
            'bandwidth_in_range': 1.0 if bandwidth_in_range else 0.0,
            'primary_dislocation_confirmation': 1.0 if abs(p_z) >= 0.8 else 0.0,
            'override_dislocation_confirmation': 1.0 if abs(e_z) >= 0.5 else 0.0,
            'low_burst_confirmation': 1.0 if trade_burst < cfg.range_trade_burst_max else 0.0,
            'trend_pressure_penalty': -1.0 if trend_pressure else 0.0,
            'burst_conflict_penalty': -1.0 if bursty else 0.0,
        }
        if subscores['primary_dislocation_confirmation']:
            reversion_score += 1.0
        if subscores['override_dislocation_confirmation']:
            reversion_score += 1.0
        if subscores['low_burst_confirmation']:
            reversion_score += 1.0

        blockers: list[str] = []
        if p_adx > cfg.range_primary_adx_max:
            blockers.append('primary_adx_above_range_threshold')
        if not bandwidth_in_range:
            blockers.append('bandwidth_outside_range_window')
        if trend_pressure:
            blockers.append('background_trend_pressure')
        if bursty:
            blockers.append('burst_conflict')

        signals = {
            'p_adx': p_adx,
            'p_z': p_z,
            'p_bw': p_bw,
            'e_z': e_z,
            'trade_burst': trade_burst,
            'bg_adx': bg_adx,
            'bg_slope20': bg_slope20,
            'bg_slope50': bg_slope50,
            'trend_pressure': trend_pressure,
            'bursty': bursty,
            'bandwidth_in_range': bandwidth_in_range,
        }

        if p_adx <= cfg.range_primary_adx_max and bandwidth_in_range:
            if reversion_score >= cfg.range_reversion_enter_min and not trend_pressure and not bursty:
                return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='range_reversion_confirmed', score=reversion_score, blockers=blockers, signals=signals, subscores=subscores)
            if reversion_score >= cfg.range_reversion_arm_min and not trend_pressure:
                return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='range_reversion_arming', score=reversion_score, blockers=blockers, signals=signals, subscores=subscores)

        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='range_wait_or_breakout_risk', score=reversion_score, blockers=blockers, signals=signals, subscores=subscores)


class CompressionExecutor(BaseExecutor):
    regime = 'compression'

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        cfg = self.settings(output)
        account = output.route_decision['account']
        bw = float(output.primary_features.get('bollinger_bandwidth_pct') or 0.0)
        rv = float(output.primary_features.get('realized_vol_pct') or 0.0)
        z15 = float(output.primary_features.get('vwap_deviation_z') or 0.0)
        z1 = float(output.override_features.get('vwap_deviation_z') or 0.0)
        trade_burst = float(output.override_features.get('trade_burst_score') or 0.0)
        basis = float(output.primary_features.get('basis_deviation_pct') or 0.0)
        oi_accel = float(output.primary_features.get('oi_accel') or 0.0)
        bg_slope = float(output.background_features.get('ema20_slope') or 0.0)

        compression_regime = bw <= cfg.compression_bandwidth_max and rv <= cfg.compression_realized_vol_max
        structure_block = abs(basis) >= 0.02 and abs(oi_accel) >= 0.5
        launch_bias = 0.0
        subscores = {
            'bandwidth_compression_confirmation': 1.0 if bw <= cfg.compression_bandwidth_max else 0.0,
            'realized_vol_compression_confirmation': 1.0 if rv <= cfg.compression_realized_vol_max else 0.0,
            'override_dislocation_confirmation': 1.0 if abs(z1) >= 1.0 else 0.0,
            'primary_dislocation_confirmation': 1.0 if abs(z15) >= 0.9 else 0.0,
            'trade_burst_confirmation': 1.0 if trade_burst >= cfg.compression_trade_burst_min else 0.0,
            'structure_block_penalty': -1.0 if structure_block else 0.0,
        }
        if subscores['override_dislocation_confirmation']:
            launch_bias += 1.0
        if subscores['primary_dislocation_confirmation']:
            launch_bias += 1.0
        if subscores['trade_burst_confirmation']:
            launch_bias += 1.0

        blockers: list[str] = []
        if bw > cfg.compression_bandwidth_max:
            blockers.append('bandwidth_not_compressed')
        if rv > cfg.compression_realized_vol_max:
            blockers.append('realized_vol_not_compressed')
        if structure_block:
            blockers.append('structure_block')

        signals = {
            'bw': bw,
            'rv': rv,
            'z15': z15,
            'z1': z1,
            'trade_burst': trade_burst,
            'basis': basis,
            'oi_accel': oi_accel,
            'bg_slope': bg_slope,
            'compression_regime': compression_regime,
            'structure_block': structure_block,
        }

        if compression_regime:
            if launch_bias >= cfg.compression_launch_bias_enter_min and not structure_block:
                side = 'long' if bg_slope >= 0 else 'short'
                if abs(z1) >= 1.0:
                    side = 'long' if z1 > 0 else 'short'
                return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='compression_breakout_confirmed', score=launch_bias, blockers=blockers, signals=signals, subscores=subscores)

            if launch_bias >= cfg.compression_launch_bias_arm_min:
                side = 'long' if bg_slope >= 0 else 'short'
                if abs(z1) >= 0.8:
                    side = 'long' if z1 > 0 else 'short'
                return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='compression_breakout_arming', score=launch_bias, blockers=blockers, signals=signals, subscores=subscores)

        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='compression_wait_or_probe', score=launch_bias, blockers=blockers, signals=signals, subscores=subscores)


class CrowdedExecutor(BaseExecutor):
    regime = 'crowded'

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        cfg = self.settings(output)
        account = output.route_decision['account']
        funding = float(output.primary_features.get('funding_pctile') or 0.5)
        oi_accel = float(output.primary_features.get('oi_accel') or 0.0)
        basis = float(output.primary_features.get('basis_deviation_pct') or 0.0)
        p_z = float(output.primary_features.get('vwap_deviation_z') or 0.0)
        e_z = float(output.override_features.get('vwap_deviation_z') or 0.0)
        trade_burst = float(output.override_features.get('trade_burst_score') or 0.0)

        crowd_extreme = max(funding, 1.0 - funding)
        side = 'short' if basis >= 0 or p_z >= 0 else 'long'
        fast_event_conflict = trade_burst >= cfg.crowded_fast_event_trade_burst_min and abs(e_z) >= cfg.crowded_fast_event_ez_min

        rejection_score = 0.0
        subscores = {
            'crowd_extreme_confirmation': 1.0 if crowd_extreme >= cfg.crowded_extreme_min else 0.0,
            'oi_accel_confirmation': 1.0 if abs(oi_accel) >= cfg.crowded_oi_accel_min else 0.0,
            'basis_extension_confirmation': 1.0 if abs(basis) >= cfg.crowded_basis_min else 0.0,
            'price_extension_confirmation': 1.0 if abs(p_z) >= 1.2 else 0.0,
            'fast_event_conflict_penalty': -1.0 if fast_event_conflict else 0.0,
        }
        if subscores['crowd_extreme_confirmation']:
            rejection_score += 1.0
        if subscores['oi_accel_confirmation']:
            rejection_score += 1.0
        if subscores['basis_extension_confirmation']:
            rejection_score += 1.0
        if subscores['price_extension_confirmation']:
            rejection_score += 1.0

        blockers: list[str] = []
        if crowd_extreme < cfg.crowded_extreme_min:
            blockers.append('crowd_not_extreme_enough')
        if abs(oi_accel) < cfg.crowded_oi_accel_min:
            blockers.append('oi_accel_too_small')
        if abs(basis) < cfg.crowded_basis_min:
            blockers.append('basis_extension_too_small')
        if fast_event_conflict:
            blockers.append('fast_event_conflict')

        signals = {
            'funding_pctile': funding,
            'crowd_extreme': crowd_extreme,
            'oi_accel': oi_accel,
            'basis': basis,
            'p_z': p_z,
            'e_z': e_z,
            'trade_burst': trade_burst,
            'fast_event_conflict': fast_event_conflict,
        }

        if rejection_score >= cfg.crowded_rejection_enter_min and not fast_event_conflict:
            return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='crowded_reversal_confirmed', score=rejection_score, blockers=blockers, signals=signals, subscores=subscores)
        if rejection_score >= cfg.crowded_rejection_arm_min:
            return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='crowded_reversal_arming', score=rejection_score, blockers=blockers, signals=signals, subscores=subscores)
        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='crowded_wait_or_insufficient_extension', score=rejection_score, blockers=blockers, signals=signals, subscores=subscores)


class ShockExecutor(BaseExecutor):
    regime = 'shock'

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        cfg = self.settings(output)
        account = output.route_decision['account']
        e_z = float(output.override_features.get('vwap_deviation_z') or 0.0)
        trade_burst = float(output.override_features.get('trade_burst_score') or 0.0)
        liq = float(output.override_features.get('liquidation_spike_score') or 0.0)
        imbalance = abs(float(output.override_features.get('orderbook_imbalance') or 0.0))
        rv = float(output.override_features.get('realized_vol_pct') or 0.0)

        side = 'short' if e_z >= 0 else 'long'
        event_score = 0.0
        subscores = {
            'trade_burst_confirmation': 1.0 if trade_burst >= cfg.shock_trade_burst_min else 0.0,
            'liquidation_spike_confirmation': 1.0 if liq >= cfg.shock_liq_min else 0.0,
            'imbalance_confirmation': 1.0 if imbalance >= cfg.shock_imbalance_min else 0.0,
            'dislocation_confirmation': 1.0 if abs(e_z) >= 1.5 else 0.0,
            'realized_vol_confirmation': 1.0 if rv >= 0.8 else 0.0,
        }
        for key in subscores:
            if subscores[key] > 0:
                event_score += 1.0

        blockers: list[str] = []
        if trade_burst < cfg.shock_trade_burst_min:
            blockers.append('trade_burst_too_small')
        if liq < cfg.shock_liq_min:
            blockers.append('liquidation_spike_too_small')
        if imbalance < cfg.shock_imbalance_min:
            blockers.append('imbalance_too_small')
        if abs(e_z) < 1.5:
            blockers.append('dislocation_too_small')

        signals = {
            'e_z': e_z,
            'trade_burst': trade_burst,
            'liq': liq,
            'imbalance': imbalance,
            'rv': rv,
        }

        if event_score >= cfg.shock_event_enter_min:
            return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='shock_reversal_confirmed', score=event_score, blockers=blockers, signals=signals, subscores=subscores)
        if event_score >= cfg.shock_event_arm_min:
            return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='shock_reversal_arming', score=event_score, blockers=blockers, signals=signals, subscores=subscores)
        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='shock_wait_for_confirmation', score=event_score, blockers=blockers, signals=signals, subscores=subscores)


class HoldExecutor(BaseExecutor):
    regime = 'hold'

    def build_plan(self, output: RegimeRunnerOutput) -> ExecutionPlan:
        return ExecutionPlan(regime=output.final_decision['primary'], account=None, action='hold', reason='route_disabled_or_no_trade')


EXECUTORS = {
    'trend': TrendExecutor(),
    'range': RangeExecutor(),
    'compression': CompressionExecutor(),
    'crowded': CrowdedExecutor(),
    'shock': ShockExecutor(),
}


ALWAYS_ON_STRATEGY_ACCOUNT_MAP = {
    'trend': 'trend',
    'range': 'meanrev',
    'compression': 'compression',
    'crowded': 'crowded',
    'shock': 'realtime',
}


def _plan_to_dict(plan: ExecutionPlan) -> dict:
    return {
        'regime': plan.regime,
        'account': plan.account,
        'action': plan.action,
        'side': plan.side,
        'size': plan.size,
        'reason': plan.reason,
        'score': plan.score,
        'blockers': plan.blockers,
        'signals': plan.signals,
        'subscores': plan.subscores,
    }


def build_shadow_plans(output: RegimeRunnerOutput) -> dict[str, dict]:
    plans: dict[str, dict] = {}
    for name, executor in EXECUTORS.items():
        plan = executor.build_plan(output)
        plans[name] = _plan_to_dict(plan)
    return plans


def build_parallel_plans(output: RegimeRunnerOutput) -> dict[str, ExecutionPlan]:
    plans: dict[str, ExecutionPlan] = {}
    for name, executor in EXECUTORS.items():
        routed_output = RegimeRunnerOutput(
            observed_at=output.observed_at,
            symbol=output.symbol,
            background_4h=output.background_4h,
            primary_15m=output.primary_15m,
            override_1m=output.override_1m,
            background_features=output.background_features,
            primary_features=output.primary_features,
            override_features=output.override_features,
            final_decision={**output.final_decision, 'primary': name},
            route_decision={
                'regime': output.route_decision.get('regime'),
                'account': ALWAYS_ON_STRATEGY_ACCOUNT_MAP.get(name),
                'strategy_family': name,
                'trade_enabled': True,
                'allow_reason': f'always_on_{name}',
                'block_reason': None,
            },
            decision_summary={
                **output.decision_summary,
                'account': ALWAYS_ON_STRATEGY_ACCOUNT_MAP.get(name),
                'strategy_family': name,
                'trade_enabled': True,
                'allow_reason': f'always_on_{name}',
                'block_reason': None,
            },
            settings=output.settings,
        )
        plan = executor.build_plan(routed_output)
        plan.account = ALWAYS_ON_STRATEGY_ACCOUNT_MAP.get(name)
        plans[name] = plan
    return plans


def executor_for(output: RegimeRunnerOutput) -> BaseExecutor:
    regime = output.final_decision['primary']
    if not output.route_decision['trade_enabled'] or output.route_decision['account'] is None:
        return HoldExecutor()
    return EXECUTORS.get(regime, HoldExecutor())
