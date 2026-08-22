"""
Unit Tests for Portfolio SAA, PyPortfolioOpt, and Performance Attribution
"""

import pytest
import pandas as pd
import numpy as np

from cfa_quant.instruments.portfolio import UnifiedPortfolio
from cfa_quant.instruments.fixed_income import FixedCouponBond
from cfa_quant.instruments.equity import PublicEquityStock
from cfa_quant.portfolio_risk.attribution_engine import PerformanceAttributionEngine
from cfa_quant.marginal_allocation import MarginalAllocationEngine

def test_unified_portfolio_pyportfolioopt_optimization():
    port = UnifiedPortfolio("TestPort", risk_free_rate=0.045)
    
    eq = PublicEquityStock("Core Stock", beta=1.1, expected_earnings_growth=0.08, historical_volatility=0.18)
    bnd = FixedCouponBond("Treasury Bond", coupon_rate=0.045, maturity_years=7.0, yield_to_maturity=0.045)
    
    port.add_instrument(eq, 600000.0)
    port.add_instrument(bnd, 400000.0)
    
    metrics = port.compute_portfolio_metrics()
    assert metrics["expected_annual_return_pct"] > 0.0
    assert metrics["annual_volatility_pct"] > 0.0
    assert metrics["sharpe_ratio"] is not None
    
    # Run PyPortfolioOpt Max Sharpe
    opt = port.optimize_with_pyportfolioopt("max_sharpe")
    assert "optimal_weights" in opt
    assert sum(opt["optimal_weights"].values()) > 95.0, "Weights must sum to approx 100%"

def test_marginal_allocation_mctr_sum():
    port = UnifiedPortfolio("BasePort")
    port.add_instrument(PublicEquityStock("Equity", beta=1.0, expected_earnings_growth=0.07, historical_volatility=0.18), 600000.0)
    port.add_instrument(FixedCouponBond("Bond", coupon_rate=0.04, maturity_years=5.0, yield_to_maturity=0.045), 400000.0)
    
    cand = PublicEquityStock("TechStock", beta=1.2, expected_earnings_growth=0.10, historical_volatility=0.22)
    
    marg = MarginalAllocationEngine()
    sim_res, _, _, _ = marg.simulate_asset_addition(port, cand, dollar_to_add=200000.0)
    
    # Check that Percentage Contributions to Risk (%CTR) sum to ~100%
    sum_pct_ctr = sum(sim_res.mctr_contributions_pct)
    assert abs(sum_pct_ctr - 100.0) < 2.0, f"Expected %CTR to sum to 100%, got {sum_pct_ctr}%"

def test_carino_multi_period_linking():
    eng = PerformanceAttributionEngine()
    
    period_excess = [0.015, -0.005, 0.020, 0.010]
    period_alloc = [0.008, -0.002, 0.012, 0.005]
    period_select = [0.007, -0.003, 0.008, 0.005]
    
    linked = eng.compute_carino_multi_period_linking(period_excess, period_alloc, period_select)
    
    assert linked["cumulative_excess_pct"] == 4.0, "Cumulative excess must sum exactly"
    assert abs(linked["linked_allocation_pct"] + linked["linked_selection_pct"] - linked["cumulative_excess_pct"]) < 0.10, "Linked components must reconcile with cumulative excess"
