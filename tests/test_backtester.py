"""
Unit, Invariant, and Negative Tests for Walk-Forward Backtester & Slippage Simulator
"""

import pytest
import numpy as np
from cfa_quant.backtester import WalkForwardBacktester, BacktestReport

def test_walk_forward_backtester_execution_and_metrics():
    bt = WalkForwardBacktester(risk_free_rate=0.045, half_spread_bps=5.0, commission_rate_bps=2.0)
    
    np.random.seed(42)
    t_days = 252
    returns = np.random.normal(0.08 / 252.0, 0.15 / np.sqrt(252.0), size=(t_days, 2))
    prices = 100.0 * np.exp(np.cumsum(returns, axis=0))
    
    report = bt.run_backtest(
        strategy_name="60/40 Baseline",
        asset_names=["Asset A", "Asset B"],
        price_matrix=prices,
        target_weights=np.array([0.60, 0.40]),
        initial_capital=1000000.0,
        rebalance_corridor_pct=0.03
    )
    
    assert isinstance(report, BacktestReport)
    assert report.initial_capital == 1000000.0
    assert report.ending_capital > 0.0
    assert len(report.equity_curve) == t_days
    assert len(report.drawdown_series) == t_days
    assert report.max_drawdown_pct <= 0.0
    assert report.total_turnover_usd >= 1000000.0
    assert report.total_friction_drag_usd > 0.0

def test_slippage_and_friction_invariants():
    """Verify that higher transaction frictions strictly reduce net ending capital."""
    np.random.seed(42)
    prices = 100.0 * np.exp(np.cumsum(np.random.normal(0.0005, 0.01, size=(100, 2)), axis=0))
    
    bt_low_cost = WalkForwardBacktester(half_spread_bps=1.0, commission_rate_bps=0.5, market_impact_lambda=0.0001)
    bt_high_cost = WalkForwardBacktester(half_spread_bps=25.0, commission_rate_bps=15.0, market_impact_lambda=0.01)
    
    rep_low = bt_low_cost.run_backtest("Low Cost", ["A", "B"], prices, np.array([0.5, 0.5]), 1000000.0)
    rep_high = bt_high_cost.run_backtest("High Cost", ["A", "B"], prices, np.array([0.5, 0.5]), 1000000.0)
    
    assert rep_low.ending_capital > rep_high.ending_capital
    assert rep_high.total_friction_drag_usd > rep_low.total_friction_drag_usd

def test_backtester_negative_and_dimension_errors():
    bt = WalkForwardBacktester()
    prices = np.ones((50, 3))
    
    # Mismatched asset names
    with pytest.raises(ValueError, match="Asset count mismatch"):
        bt.run_backtest("Error Mandate", ["A", "B"], prices, np.array([0.5, 0.5]))
        
    # Mismatched target weights
    with pytest.raises(ValueError, match="Asset count mismatch"):
        bt.run_backtest("Error Mandate", ["A", "B", "C"], prices, np.array([0.5, 0.5]))
