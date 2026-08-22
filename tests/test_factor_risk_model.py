"""
Unit, Negative, Boundary & Mathematical Invariant Tests for Multi-Factor Risk Model & FLAM
"""

import pytest
import numpy as np
from cfa_quant.portfolio_risk.factor_risk_model import FactorRiskModelEngine, ActiveRiskDecomposition

@pytest.fixture
def factor_setup():
    engine = FactorRiskModelEngine()
    assets = ["MSFT", "AAPL", "NVDA", "JNJ", "XOM"]
    dw = np.array([0.08, -0.05, 0.06, -0.04, -0.05])
    B_matrix = np.array([
        [1.15, -0.20, -0.30,  0.40,  0.60, -0.10],
        [1.10, -0.15, -0.25,  0.30,  0.55, -0.15],
        [1.45,  0.30, -0.40,  0.85,  0.50,  0.20],
        [0.65, -0.40,  0.45, -0.20,  0.30, -0.30],
        [0.80, -0.10,  0.75, -0.15, -0.20,  0.40]
    ])
    spec_vars = np.array([0.0225, 0.0200, 0.0450, 0.0100, 0.0150])
    return engine, assets, dw, B_matrix, spec_vars

def test_factor_risk_decomposition_exact_variance_sum(factor_setup):
    engine, assets, dw, B_matrix, spec_vars = factor_setup
    decomp = engine.decompose_active_risk("ALPHA_PORT", "BMK", assets, dw, B_matrix, spec_vars, portfolio_active_return=0.030)
    
    assert isinstance(decomp, ActiveRiskDecomposition)
    assert decomp.total_tracking_error_bps > 0.0
    
    # Invariant: Factor Risk % + Specific Risk % = 100.0%
    sum_pct = decomp.factor_risk_pct_of_variance + decomp.specific_risk_pct_of_variance
    assert abs(sum_pct - 100.0) < 0.1, f"Variance percentages must sum to 100%: {sum_pct}"
    
    # Invariant: Total Active Variance = Factor Variance + Specific Variance
    f_var = (decomp.factor_active_risk_bps / 10000.0) ** 2
    s_var = (decomp.specific_active_risk_bps / 10000.0) ** 2
    tot_var = (decomp.total_tracking_error_bps / 10000.0) ** 2
    assert abs(tot_var - (f_var + s_var)) < 1e-5

def test_fundamental_law_of_active_management():
    # IC = 0.05, BR = 64, TC = 0.80
    # Expected IR_unconstrained = 0.05 * sqrt(64) = 0.05 * 8 = 0.40
    # Expected IR_constrained = 0.80 * 0.40 = 0.32
    flam = FactorRiskModelEngine.evaluate_fundamental_law(
        information_coefficient=0.05,
        breadth_number_of_bets=64,
        transfer_coefficient=0.80,
        target_tracking_error=0.040
    )
    assert abs(flam["unconstrained_ir"] - 0.40) < 1e-4
    assert abs(flam["constrained_ir"] - 0.32) < 1e-4
    assert abs(flam["expected_active_return_pct"] - 1.28) < 1e-2 # 0.32 * 4.0% = 1.28%

def test_factor_risk_negative_and_zero_active_weights(factor_setup):
    engine, assets, _, B_matrix, spec_vars = factor_setup
    
    # Zero active weights (passive index replication)
    zero_dw = np.zeros(5)
    decomp_zero = engine.decompose_active_risk("INDEX", "BMK", assets, zero_dw, B_matrix, spec_vars, portfolio_active_return=0.0)
    
    assert decomp_zero.total_tracking_error_bps == pytest.approx(0.0, abs=1e-1)
    assert decomp_zero.factor_active_risk_bps == pytest.approx(0.0, abs=1e-1)
    assert decomp_zero.specific_active_risk_bps == pytest.approx(0.0, abs=1e-1)
