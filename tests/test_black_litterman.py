"""
Unit, Negative, Boundary & Mathematical Invariant Tests for Black-Litterman Asset Allocation Model
"""

import pytest
import numpy as np
from cfa_quant.portfolio_risk.black_litterman import BlackLittermanEngine

@pytest.fixture
def bl_setup():
    assets = ["US_EQUITIES", "GLOBAL_EQUITIES", "US_TREASURIES", "EM_BONDS"]
    cov = np.array([
        [0.040, 0.025, 0.002, 0.010],
        [0.025, 0.050, 0.001, 0.015],
        [0.002, 0.001, 0.008, 0.003],
        [0.010, 0.015, 0.003, 0.025]
    ])
    w_m = np.array([0.45, 0.25, 0.20, 0.10])
    engine = BlackLittermanEngine(assets, cov, w_m, risk_aversion=2.5, tau=0.05)
    return engine, assets, cov, w_m

def test_implied_equilibrium_returns_calculation(bl_setup):
    engine, assets, cov, w_m = bl_setup
    # Pi = lambda * Sigma * w_mkt
    expected_pi = 2.5 * np.dot(cov, w_m)
    np.testing.assert_allclose(engine.pi, expected_pi, rtol=1e-5)
    assert len(engine.pi) == 4
    assert np.all(engine.pi > 0.0)

def test_bullish_view_positive_active_tilt(bl_setup):
    engine, assets, cov, w_m = bl_setup
    # Relative View: US Equities will outperform Global Equities by +3.0%
    P = np.array([[1.0, -1.0, 0.0, 0.0]])
    Q = np.array([0.030])
    conf = [0.80]
    
    res = engine.blend_views(P, Q, conf)
    
    # 1. Posterior return for US Equities must exceed its neutral equilibrium return
    assert res["posterior_expected_returns"][0] > res["implied_equilibrium_returns"][0]
    
    # 2. Optimal constrained weight for US Equities must tilt upwards (active tilt > 0)
    assert res["active_tilts"][0] > 0.0
    
    # 3. Invariant: Constrained weights sum to 1.0
    assert abs(sum(res["optimal_constrained_weights"]) - 1.0) < 1e-4
    
    # 4. Invariant: Sum of active tilts sums to 0.0
    assert abs(sum(res["active_tilts"])) < 1e-4
    
    # 5. Invariant: Long-only weights strictly non-negative
    assert all(w >= 0.0 for w in res["optimal_constrained_weights"])

def test_black_litterman_negative_and_dimension_errors(bl_setup):
    engine, assets, cov, w_m = bl_setup
    
    # Negative Test 1: P matrix with mismatched column dimensions (3 columns instead of 4)
    invalid_P = np.array([[1.0, -1.0, 0.0]])
    invalid_Q = np.array([0.02])
    with pytest.raises(ValueError, match="P matrix columns"):
        engine.blend_views(invalid_P, invalid_Q)

def test_extreme_confidence_and_unnormalized_weights():
    # Boundary Test: Unnormalized market weights (sum to 2.0 instead of 1.0)
    assets = ["A", "B"]
    cov = np.eye(2) * 0.04
    w_unnorm = np.array([1.0, 1.0])
    
    engine = BlackLittermanEngine(assets, cov, w_unnorm, risk_aversion=3.0)
    # Market weights should auto-normalize to [0.5, 0.5]
    np.testing.assert_allclose(engine.w_mkt, [0.5, 0.5], rtol=1e-5)
    
    # Boundary Test: 0% and 100% confidence clipping
    P = np.array([[1.0, 0.0]])
    Q = np.array([0.10])
    res_zero_conf = engine.blend_views(P, Q, confidences=[0.0])
    res_high_conf = engine.blend_views(P, Q, confidences=[1.0])
    
    assert res_zero_conf["optimal_constrained_weights"][0] >= 0.0
    assert res_high_conf["optimal_constrained_weights"][0] >= 0.0
