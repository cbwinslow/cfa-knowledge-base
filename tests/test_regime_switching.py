"""
Unit, Invariant, and Negative Tests for Markov Regime-Switching & Merton Jump-Diffusion Simulator
"""

import pytest
import numpy as np
from cfa_quant.simulation.regime_switching import (
    BaseStochasticSimulator,
    RegimeState,
    SimulationResult,
    MarkovRegimeEngine,
    MertonJumpDiffusionEngine
)

def test_polymorphic_stochastic_simulator_contract():
    """Verify that both Markov and Merton engines satisfy Liskov Substitution on BaseStochasticSimulator."""
    r1 = RegimeState(0, "Expansion", annual_drift=0.10, annual_volatility=0.15)
    r2 = RegimeState(1, "Recession", annual_drift=-0.05, annual_volatility=0.28)
    P = np.array([[0.90, 0.10], [0.25, 0.75]])
    
    simulators: list[BaseStochasticSimulator] = [
        MarkovRegimeEngine(initial_spot=100.0, regimes=[r1, r2], transition_matrix=P),
        MertonJumpDiffusionEngine(initial_spot=100.0, annual_drift=0.08, annual_volatility=0.18, jump_intensity=1.5)
    ]
    
    for sim in simulators:
        res = sim.simulate_paths(num_paths=100, time_horizon_years=0.5, steps_per_year=100, seed=42)
        assert isinstance(res, SimulationResult)
        assert res.initial_spot == 100.0
        assert res.num_paths == 100
        assert res.paths_matrix.shape == (100, 51)
        assert res.terminal_prices.shape == (100,)
        assert np.all(res.paths_matrix > 0.0) # Strictly positive asset price invariant
        assert res.expected_terminal_price > 0.0
        assert res.max_path_drawdown_pct <= 0.0

def test_markov_stationary_distribution_ergodic_invariants():
    r1 = RegimeState(0, "Bull", annual_drift=0.12, annual_volatility=0.14)
    r2 = RegimeState(1, "Bear", annual_drift=-0.10, annual_volatility=0.30)
    P = np.array([[0.80, 0.20], [0.40, 0.60]])
    
    engine = MarkovRegimeEngine(initial_spot=100.0, regimes=[r1, r2], transition_matrix=P)
    pi = engine.compute_stationary_distribution()
    
    # 1. Probabilities sum to 1.0
    assert np.sum(pi) == pytest.approx(1.0, abs=1e-5)
    
    # 2. Stationary equilibrium condition: pi * P == pi
    pi_next = np.dot(pi, P)
    np.testing.assert_allclose(pi, pi_next, atol=1e-5)

def test_merton_jump_diffusion_fat_tails():
    # Higher jump intensity generates elevated kurtosis
    merton_jumps = MertonJumpDiffusionEngine(initial_spot=100.0, annual_drift=0.08, annual_volatility=0.12, jump_intensity=5.0, jump_mean_log=-0.10, jump_vol_log=0.15)
    res = merton_jumps.simulate_paths(num_paths=1000, time_horizon_years=1.0, steps_per_year=252, seed=42)
    
    assert np.all(res.paths_matrix > 0.0)
    assert res.terminal_var_99_pct < res.terminal_var_95_pct
    assert res.terminal_cvar_95_pct <= res.terminal_var_95_pct

def test_regime_switching_negative_and_dimension_errors():
    # Negative initial spot
    with pytest.raises(ValueError, match="strictly positive"):
        MertonJumpDiffusionEngine(initial_spot=-50.0)
        
    # Transition matrix dimension mismatch
    r1 = RegimeState(0, "A", 0.05, 0.1)
    r2 = RegimeState(1, "B", 0.05, 0.1)
    with pytest.raises(ValueError, match="Transition matrix must have shape"):
        MarkovRegimeEngine(initial_spot=100.0, regimes=[r1, r2], transition_matrix=np.ones((3, 3)) / 3.0)
        
    # Non-normalized transition matrix row sums
    P_invalid = np.array([[0.8, 0.1], [0.3, 0.7]]) # Row 0 sums to 0.9 != 1.0
    with pytest.raises(ValueError, match="must sum exactly to 1.0"):
        MarkovRegimeEngine(initial_spot=100.0, regimes=[r1, r2], transition_matrix=P_invalid)
