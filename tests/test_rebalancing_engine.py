"""
Unit, Negative, Boundary & Invariant Tests for Tax-Aware Portfolio Rebalancing Engine
"""

import pytest
import numpy as np
from cfa_quant.portfolio_risk.rebalancing_engine import PortfolioRebalancingEngine, RebalancingBlotter, TradeOrder

@pytest.fixture
def rebalance_setup():
    engine = PortfolioRebalancingEngine(capital_gains_tax_rate=0.238, default_corridor_band_pct=0.03)
    curr_pos = {
        "AAPL": {"shares": 400.0, "price": 240.0, "cost_basis": 180.0},
        "MSFT": {"shares": 250.0, "price": 480.0, "cost_basis": 500.0},
        "US10Y": {"shares": 500.0, "price": 100.0, "cost_basis": 100.0}
    }
    tgt_weights = {
        "AAPL": 0.20,      # Overweight -> should SELL
        "MSFT": 0.30,      # Overweight -> should SELL
        "US10Y": 0.50      # Underweight -> should BUY
    }
    return engine, curr_pos, tgt_weights

def test_rebalancing_order_generation_and_direction(rebalance_setup):
    engine, curr_pos, tgt_weights = rebalance_setup
    blotter = engine.construct_rebalancing_orders("TEST_PORTFOLIO", curr_pos, tgt_weights, cash_balance=0.0)
    
    assert isinstance(blotter, RebalancingBlotter)
    assert len(blotter.orders) > 0
    assert blotter.total_portfolio_value_usd == (400*240 + 250*480 + 500*100) # $266,000
    
    order_map = {o.symbol: o for o in blotter.orders}
    
    # AAPL is currently $96k (~36%) vs target 20% -> must generate SELL
    assert "AAPL" in order_map
    assert order_map["AAPL"].action == "SELL"
    assert order_map["AAPL"].estimated_realized_gain_usd > 0.0  # Selling at $240 vs $180 basis
    
    # MSFT is currently $120k (~45%) vs target 30% -> must generate SELL
    assert "MSFT" in order_map
    assert order_map["MSFT"].action == "SELL"
    assert order_map["MSFT"].estimated_realized_gain_usd < 0.0  # Loss harvest at $480 vs $500 basis
    
    # US10Y is currently $50k (~19%) vs target 50% -> must generate BUY
    assert "US10Y" in order_map
    assert order_map["US10Y"].action == "BUY"

def test_rebalancing_corridor_filtering_skips_immaterial_drift():
    engine = PortfolioRebalancingEngine(default_corridor_band_pct=0.05)
    
    # Position with only 1% drift (within 5% corridor)
    curr_pos = {"SPY": {"shares": 1000.0, "price": 100.0, "cost_basis": 90.0}} # $100k (100%)
    tgt_weights = {"SPY": 0.99} # 99% (drift = -1% < 5% band)
    
    blotter = engine.construct_rebalancing_orders("CORRIDOR_TEST", curr_pos, tgt_weights, cash_balance=0.0, enable_corridor_filtering=True)
    assert len(blotter.orders) == 0, "Should generate zero orders within corridor band"

def test_optimal_corridor_width_sensitivities():
    engine = PortfolioRebalancingEngine()
    
    # CFA Invariant: Higher volatility yields narrower corridor width
    width_low_vol = engine.calculate_optimal_corridor_width(asset_volatility=0.10, transaction_cost_pct=0.001, tax_rate=0.20)
    width_high_vol = engine.calculate_optimal_corridor_width(asset_volatility=0.35, transaction_cost_pct=0.001, tax_rate=0.20)
    assert width_low_vol > width_high_vol, f"Low vol ({width_low_vol}) should have wider corridor than high vol ({width_high_vol})"
    
    # CFA Invariant: Higher transaction costs yield wider corridor width
    width_low_cost = engine.calculate_optimal_corridor_width(asset_volatility=0.20, transaction_cost_pct=0.0005, tax_rate=0.20)
    width_high_cost = engine.calculate_optimal_corridor_width(asset_volatility=0.20, transaction_cost_pct=0.0050, tax_rate=0.20)
    assert width_high_cost > width_low_cost

def test_rebalancing_empty_and_negative_inputs():
    engine = PortfolioRebalancingEngine()
    
    # Test completely empty positions with 0 cash
    empty_blotter = engine.construct_rebalancing_orders("EMPTY", {}, {}, cash_balance=0.0)
    assert len(empty_blotter.orders) == 0
    assert empty_blotter.total_portfolio_value_usd == 0.0
