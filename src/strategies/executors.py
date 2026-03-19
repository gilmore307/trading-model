from __future__ import annotations

from dataclasses import dataclass

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

        if bg_adx >= cfg.trend_bg_adx_min and aligned:
            follow_through = 0.0
            if p_adx >= cfg.trend_primary_adx_min:
                follow_through += 1.0
            if abs(p_z) >= 0.6:
                follow_through += 1.0
            if abs(e_z) >= 0.8:
                follow_through += 1.0
            if trade_burst >= cfg.trend_trade_burst_min:
                follow_through += 1.0

            stretched = abs(p_z) >= 2.2 and abs(e_z) >= 1.8
            compressed_pause = p_bw <= 0.015 and trade_burst < cfg.trend_trade_burst_min

            if follow_through >= cfg.trend_follow_through_enter_min and not stretched:
                return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='trend_follow_through_confirmed')
            if follow_through >= cfg.trend_follow_through_arm_min and not compressed_pause:
                return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='trend_setup_arming')

        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='trend_wait_or_overextended')


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

        if p_adx <= cfg.range_primary_adx_max and 0.08 <= p_bw <= 0.30:
            reversion_score = 0.0
            if abs(p_z) >= 0.8:
                reversion_score += 1.0
            if abs(e_z) >= 0.5:
                reversion_score += 1.0
            if trade_burst < cfg.range_trade_burst_max:
                reversion_score += 1.0

            if reversion_score >= cfg.range_reversion_enter_min and not trend_pressure and not bursty:
                return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='range_reversion_confirmed')
            if reversion_score >= cfg.range_reversion_arm_min and not trend_pressure:
                return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='range_reversion_arming')

        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='range_wait_or_breakout_risk')


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

        if bw <= cfg.compression_bandwidth_max and rv <= cfg.compression_realized_vol_max:
            launch_bias = 0.0
            if abs(z1) >= 1.0:
                launch_bias += 1.0
            if abs(z15) >= 0.9:
                launch_bias += 1.0
            if trade_burst >= cfg.compression_trade_burst_min:
                launch_bias += 1.0

            structure_block = abs(basis) >= 0.02 and abs(oi_accel) >= 0.5
            if launch_bias >= cfg.compression_launch_bias_enter_min and not structure_block:
                side = 'long' if bg_slope >= 0 else 'short'
                if abs(z1) >= 1.0:
                    side = 'long' if z1 > 0 else 'short'
                return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='compression_breakout_confirmed')

            if launch_bias >= cfg.compression_launch_bias_arm_min:
                side = 'long' if bg_slope >= 0 else 'short'
                if abs(z1) >= 0.8:
                    side = 'long' if z1 > 0 else 'short'
                return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='compression_breakout_arming')

        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='compression_wait_or_probe')


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

        rejection_score = 0.0
        if crowd_extreme >= cfg.crowded_extreme_min:
            rejection_score += 1.0
        if abs(oi_accel) >= cfg.crowded_oi_accel_min:
            rejection_score += 1.0
        if abs(basis) >= cfg.crowded_basis_min:
            rejection_score += 1.0
        if abs(p_z) >= 1.2:
            rejection_score += 1.0

        fast_event_conflict = trade_burst >= cfg.crowded_fast_event_trade_burst_min and abs(e_z) >= cfg.crowded_fast_event_ez_min
        if rejection_score >= cfg.crowded_rejection_enter_min and not fast_event_conflict:
            return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='crowded_reversal_confirmed')
        if rejection_score >= cfg.crowded_rejection_arm_min:
            return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='crowded_reversal_arming')
        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='crowded_wait_or_insufficient_extension')


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
        if trade_burst >= cfg.shock_trade_burst_min:
            event_score += 1.0
        if liq >= cfg.shock_liq_min:
            event_score += 1.0
        if imbalance >= cfg.shock_imbalance_min:
            event_score += 1.0
        if abs(e_z) >= 1.5:
            event_score += 1.0
        if rv >= 0.8:
            event_score += 1.0

        if event_score >= cfg.shock_event_enter_min:
            return ExecutionPlan(regime=self.regime, account=account, action='enter', side=side, size=1.0, reason='shock_reversal_confirmed')
        if event_score >= cfg.shock_event_arm_min:
            return ExecutionPlan(regime=self.regime, account=account, action='arm', side=side, size=1.0, reason='shock_reversal_arming')
        return ExecutionPlan(regime=self.regime, account=account, action='watch', reason='shock_wait_for_confirmation')


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


def build_shadow_plans(output: RegimeRunnerOutput) -> dict[str, dict]:
    plans: dict[str, dict] = {}
    for name, executor in EXECUTORS.items():
        plan = executor.build_plan(output)
        plans[name] = {
            'regime': plan.regime,
            'account': plan.account,
            'action': plan.action,
            'side': plan.side,
            'size': plan.size,
            'reason': plan.reason,
        }
    return plans


def executor_for(output: RegimeRunnerOutput) -> BaseExecutor:
    regime = output.final_decision['primary']
    if not output.route_decision['trade_enabled'] or output.route_decision['account'] is None:
        return HoldExecutor()
    return EXECUTORS.get(regime, HoldExecutor())
