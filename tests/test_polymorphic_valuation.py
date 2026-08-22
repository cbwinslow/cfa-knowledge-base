"""
Unit, Negative, Boundary & Polymorphic Invariant Tests for Equity Valuation Hierarchy
"""

import pytest
import numpy as np
from cfa_quant.valuation.polymorphic_valuation import (
    BaseValuationModel,
    ThreeStageDcfValuation,
    ResidualIncomeValuation,
    DividendDiscountModelValuation,
    MarketMultiplesValuation,
    UnifiedValuationSuite
)

@pytest.fixture
def sample_financial_data():
    return {
        "free_cash_flow": 60000000000.0,
        "book_value_of_equity": 220000000000.0,
        "dividend_per_share": 3.20,
        "eps_ttm": 13.50,
        "ebitda": 110000000000.0,
        "net_debt": -30000000000.0
    }

def test_polymorphic_liskov_substitution(sample_financial_data):
    """
    Polymorphism Test: Every model can be invoked via the uniform BaseValuationModel contract.
    """
    models = [
        ThreeStageDcfValuation(stage1_years=5, stage1_growth=0.10),
        ResidualIncomeValuation(roe_forecast=0.20, forecast_years=5),
        DividendDiscountModelValuation(dividend_growth_stage1=0.07),
        MarketMultiplesValuation(target_pe_multiple=25.0)
    ]
    
    for m in models:
        assert isinstance(m, BaseValuationModel)
        assert len(m.model_name) > 0
        assert len(m.methodology) > 0
        
        output = m.calculate_intrinsic_value("TEST", sample_financial_data, cost_of_capital=0.085, shares_outstanding=7000000000.0)
        assert output.intrinsic_value_per_share > 0.0
        assert output.equity_value_usd is not None and output.equity_value_usd > 0.0

def test_unified_valuation_suite_consensus(sample_financial_data):
    suite = UnifiedValuationSuite()
    res = suite.evaluate_all_models("MSFT", sample_financial_data, cost_of_capital=0.0825, shares_outstanding=7430000000.0)
    
    assert res["ticker"] == "MSFT"
    assert res["consensus_mean_value_per_share"] > 0.0
    assert res["consensus_median_value_per_share"] > 0.0
    assert res["intrinsic_valuation_range"]["min"] <= res["intrinsic_valuation_range"]["max"]
    assert len(res["model_outputs"]) == 4

def test_valuation_cost_of_capital_monotonicity(sample_financial_data):
    """
    Invariant Test: Higher discount rate (r) strictly lowers DCF and DDM intrinsic values.
    dV / dr < 0
    """
    dcf = ThreeStageDcfValuation()
    ddm = DividendDiscountModelValuation()
    
    v_dcf_low_r = dcf.calculate_intrinsic_value("TEST", sample_financial_data, cost_of_capital=0.07, shares_outstanding=7e9).intrinsic_value_per_share
    v_dcf_high_r = dcf.calculate_intrinsic_value("TEST", sample_financial_data, cost_of_capital=0.10, shares_outstanding=7e9).intrinsic_value_per_share
    
    v_ddm_low_r = ddm.calculate_intrinsic_value("TEST", sample_financial_data, cost_of_capital=0.07, shares_outstanding=7e9).intrinsic_value_per_share
    v_ddm_high_r = ddm.calculate_intrinsic_value("TEST", sample_financial_data, cost_of_capital=0.10, shares_outstanding=7e9).intrinsic_value_per_share
    
    assert v_dcf_low_r > v_dcf_high_r, f"DCF failed monotonicity: {v_dcf_low_r} vs {v_dcf_high_r}"
    assert v_ddm_low_r > v_ddm_high_r, f"DDM failed monotonicity: {v_ddm_low_r} vs {v_ddm_high_r}"

def test_valuation_negative_and_corrupt_inputs():
    """
    Negative Test: Test empty dictionary, zero shares outstanding, and discount rate below terminal growth.
    """
    dcf = ThreeStageDcfValuation(stage3_terminal_growth=0.04)
    
    # 1. Test discount rate lower than terminal growth (r = 0.03 <= g = 0.04)
    # Must auto-adjust r without dividing by zero or throwing exception
    out_conv = dcf.calculate_intrinsic_value("TEST", {}, cost_of_capital=0.03, shares_outstanding=1000000.0)
    assert out_conv.intrinsic_value_per_share > 0.0
    
    # 2. Test zero shares outstanding fallback
    out_zero_shares = dcf.calculate_intrinsic_value("TEST", {}, cost_of_capital=0.08, shares_outstanding=0.0)
    assert out_zero_shares.intrinsic_value_per_share == 100.0
