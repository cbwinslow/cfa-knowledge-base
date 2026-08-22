"""
Unit, Invariant, Negative, and Boundary Tests for Options Strategy & Greeks Hedging Engine
"""

import pytest
import numpy as np
from cfa_quant.instruments.options_strategies import (
    BaseOptionStrategy,
    OptionLeg,
    OptionType,
    TradeAction,
    CoveredCallStrategy,
    ProtectiveCollarStrategy,
    BullCallSpreadStrategy,
    IronCondorStrategy,
    LongStraddleStrategy,
    GreeksHedgingSolver
)

def test_polymorphic_options_strategy_hierarchy():
    """Verify that all concrete strategies satisfy Liskov Substitution on BaseOptionStrategy."""
    strategies: list[BaseOptionStrategy] = [
        CoveredCallStrategy(spot_price_entry=500.0, call_strike=520.0, time_to_expiry_years=0.25, implied_volatility=0.20),
        ProtectiveCollarStrategy(spot_price_entry=500.0, put_strike=480.0, call_strike=525.0, time_to_expiry_years=0.25, implied_volatility=0.20),
        BullCallSpreadStrategy(spot_price_entry=500.0, lower_strike_k1=490.0, upper_strike_k2=530.0, time_to_expiry_years=0.25, implied_volatility=0.20),
        IronCondorStrategy(spot_price_entry=500.0, put_long_k1=460.0, put_short_k2=480.0, call_short_k3=520.0, call_long_k4=540.0, time_to_expiry_years=0.25, implied_volatility=0.20),
        LongStraddleStrategy(spot_price_entry=500.0, strike_price=500.0, time_to_expiry_years=0.25, implied_volatility=0.20)
    ]
    
    spots = np.array([400.0, 480.0, 500.0, 520.0, 600.0])
    
    for strat in strategies:
        payoff = strat.compute_payoff(spots)
        pnl = strat.compute_profit_loss(spots)
        bes = strat.get_break_even_points()
        max_p, max_l = strat.get_max_profit_and_loss()
        greeks = strat.compute_portfolio_greeks(current_spot=500.0)
        
        assert len(payoff) == len(spots)
        assert len(pnl) == len(spots)
        assert isinstance(bes, list)
        assert len(bes) >= 1
        assert "total_delta" in greeks
        assert "total_gamma" in greeks
        assert "total_vega_per_1pct" in greeks

def test_covered_call_and_collar_payoffs_and_breakevens():
    # 1. Covered Call
    cc = CoveredCallStrategy(spot_price_entry=100.0, call_strike=105.0, time_to_expiry_years=0.25, implied_volatility=0.20, call_premium=3.0, shares_quantity=100.0)
    be = cc.get_break_even_points()
    assert be == [97.0]  # S_0 - premium = 100 - 3
    
    max_p, max_l = cc.get_max_profit_and_loss()
    assert max_p == (105.0 - 100.0 + 3.0) * 100.0  # $800.0
    assert max_l == - (100.0 - 3.0) * 100.0        # -$9,700.0
    
    # 2. Protective Collar
    collar = ProtectiveCollarStrategy(
        spot_price_entry=100.0,
        put_strike=95.0,
        call_strike=110.0,
        time_to_expiry_years=0.25,
        implied_volatility=0.20,
        put_premium=2.50,
        call_premium=2.50, # Zero-cost collar
        shares_quantity=100.0
    )
    assert collar.net_premium_debit_per_share == 0.0
    assert collar.get_break_even_points() == [100.0]
    col_max_p, col_max_l = collar.get_max_profit_and_loss()
    assert col_max_p == (110.0 - 100.0) * 100.0   # $1,000.0
    assert col_max_l == (95.0 - 100.0) * 100.0    # -$500.0

def test_iron_condor_invariants_and_max_profit():
    ic = IronCondorStrategy(
        spot_price_entry=100.0,
        put_long_k1=85.0,
        put_short_k2=90.0,
        call_short_k3=110.0,
        call_long_k4=115.0,
        time_to_expiry_years=0.10,
        implied_volatility=0.25
    )
    max_p, max_l = ic.get_max_profit_and_loss()
    assert max_p > 0.0
    assert max_l < 0.0
    
    # Wing width = 5.0 ($500 per contract). Max Profit + |Max Loss| == Wing Width ($500)
    total_spread = max_p + abs(max_l)
    assert total_spread == pytest.approx(500.0, abs=1e-2)

def test_greeks_hedging_solver_delta_gamma_vega_neutral():
    port_delta = 450.0
    port_gamma = 15.0
    port_vega = 60.0
    
    h1_greeks = {"delta": 40.0, "gamma": 3.0, "vega": 10.0}
    h2_greeks = {"delta": -25.0, "gamma": 1.5, "vega": 18.0}
    
    hedge = GreeksHedgingSolver.solve_vega_gamma_delta_neutral_hedging(
        port_delta, port_gamma, port_vega, h1_greeks, h2_greeks
    )
    
    assert hedge["target"] == "VEGA_GAMMA_DELTA_NEUTRAL"
    assert hedge["residual_delta"] == pytest.approx(0.0, abs=1e-5)
    assert hedge["residual_gamma"] == pytest.approx(0.0, abs=1e-5)
    assert hedge["residual_vega"] == pytest.approx(0.0, abs=1e-5)

def test_options_negative_and_boundary_errors():
    # Negative strike
    with pytest.raises(ValueError, match="strictly positive"):
        OptionLeg(OptionType.CALL, TradeAction.BUY, strike_price=-10.0, time_to_expiry_years=0.1, implied_volatility=0.2)
        
    # Inverted collar strikes
    with pytest.raises(ValueError, match="strictly less"):
        ProtectiveCollarStrategy(spot_price_entry=100.0, put_strike=110.0, call_strike=90.0, time_to_expiry_years=0.1, implied_volatility=0.2)
        
    # Inverted Bull Spread
    with pytest.raises(ValueError, match="must be < upper"):
        BullCallSpreadStrategy(spot_price_entry=100.0, lower_strike_k1=110.0, upper_strike_k2=90.0, time_to_expiry_years=0.1, implied_volatility=0.2)
        
    # Collinear Hedging Matrix
    h1_collinear = {"delta": 50.0, "gamma": 2.0, "vega": 10.0}
    h2_collinear = {"delta": 100.0, "gamma": 4.0, "vega": 20.0} # Exact multiple of h1
    with pytest.raises(ValueError, match="singular"):
        GreeksHedgingSolver.solve_vega_gamma_delta_neutral_hedging(100.0, 10.0, 50.0, h1_collinear, h2_collinear)
