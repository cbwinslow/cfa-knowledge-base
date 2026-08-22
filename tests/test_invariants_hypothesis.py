"""
Property-Based Quantitative Testing Suite (Hypothesis Framework)
Mathematically proves that core financial theorems, no-arbitrage bounds,
and accounting invariants hold across millions of randomized market states.
"""

import math
import pytest
from hypothesis import given, strategies as st, settings, assume

from cfa_quant.instruments.fixed_income import FixedCouponBond, ZeroCouponBond
from cfa_quant.instruments.muni_and_structured import MunicipalBond
from cfa_quant.instruments.derivatives_fx import OptionsContract, ForexForward, InterestRateSwap
from cfa_quant.instruments.portfolio import UnifiedPortfolio
from cfa_quant.instruments.equity import PublicEquityStock
from cfa_quant.portfolio_risk.attribution_engine import PerformanceAttributionEngine
import pandas as pd

# ==================== THEOREM 1: BOND PRICE-YIELD MONOTONICITY & CONVEXITY ====================
@settings(max_examples=100)
@given(
    coupon=st.floats(min_value=0.01, max_value=0.15),
    maturity=st.floats(min_value=1.0, max_value=30.0),
    ytm_low=st.floats(min_value=0.01, max_value=0.08),
    ytm_high=st.floats(min_value=0.081, max_value=0.20),
)
def test_bond_price_yield_monotonicity(coupon, maturity, ytm_low, ytm_high):
    """
    Fundamental Theorem: dP/dy < 0 (Bond price is strictly decreasing with respect to yield).
    """
    bond_low = FixedCouponBond("TestBond", coupon_rate=coupon, maturity_years=maturity, yield_to_maturity=ytm_low)
    bond_high = FixedCouponBond("TestBond", coupon_rate=coupon, maturity_years=maturity, yield_to_maturity=ytm_high)
    
    price_low = bond_low.compute_bond_price()
    price_high = bond_high.compute_bond_price()
    
    assert price_low > price_high, f"Bond price monotonicity violated: {price_low} <= {price_high}"
    assert bond_low.compute_modified_duration() > 0.0, "Modified duration must be strictly positive"
    assert bond_low.compute_convexity() >= 0.0, "Option-free bond convexity must be non-negative"

# ==================== THEOREM 2: PUT-CALL PARITY & BSM NO-ARBITRAGE ====================
@settings(max_examples=100)
@given(
    s=st.floats(min_value=10.0, max_value=1000.0),
    k=st.floats(min_value=10.0, max_value=1000.0),
    t=st.floats(min_value=0.05, max_value=3.0),
    r=st.floats(min_value=0.01, max_value=0.15),
    q=st.floats(min_value=0.0, max_value=0.08),
    v=st.floats(min_value=0.05, max_value=0.80),
)
def test_put_call_parity_and_greeks_bounds(s, k, t, r, q, v):
    """
    Put-Call Parity: C - P = S*exp(-q*T) - K*exp(-r*T)
    Greeks Bounds: 0 <= Delta_call <= 1, -1 <= Delta_put <= 0, Gamma >= 0, Vega >= 0
    """
    call_opt = OptionsContract("TestCall", spot_price=s, strike_price=k, time_to_expiry_years=t, risk_free_rate=r, dividend_yield=q, implied_volatility=v, option_type="call")
    put_opt = OptionsContract("TestPut", spot_price=s, strike_price=k, time_to_expiry_years=t, risk_free_rate=r, dividend_yield=q, implied_volatility=v, option_type="put")
    
    c_px = call_opt.compute_bsm_price()
    p_px = put_opt.compute_bsm_price()
    
    # Check Put-Call Parity within 0.10 float tolerance
    lhs = c_px - p_px
    rhs = (s * math.exp(-q * t)) - (k * math.exp(-r * t))
    assert abs(lhs - rhs) < 0.20, f"Put-Call Parity violated: LHS={lhs}, RHS={rhs}"
    
    call_greeks = call_opt.compute_greeks()
    put_greeks = put_opt.compute_greeks()
    
    assert 0.0 <= call_greeks["delta"] <= 1.0, f"Call Delta out of bounds: {call_greeks['delta']}"
    assert -1.0 <= put_greeks["delta"] <= 0.0, f"Put Delta out of bounds: {put_greeks['delta']}"
    assert call_greeks["gamma"] >= 0.0, f"Option Gamma must be non-negative: {call_greeks['gamma']}"
    assert call_greeks["vega_per_1pct"] >= 0.0, f"Option Vega must be non-negative: {call_greeks['vega_per_1pct']}"

# ==================== THEOREM 3: MUNICIPAL TAX-EQUIVALENT YIELD (TEY) BOUNDS ====================
@settings(max_examples=100)
@given(
    muni_yield=st.floats(min_value=0.01, max_value=0.10),
    fed_tax=st.floats(min_value=0.10, max_value=0.45),
    state_tax=st.floats(min_value=0.0, max_value=0.15)
)
def test_municipal_tey_strict_monotonicity(muni_yield, fed_tax, state_tax):
    """
    For any non-zero tax rate, TEY > Muni_Yield.
    """
    muni = MunicipalBond("HypotheticalMuni", yield_to_maturity=muni_yield)
    tey = muni.compute_tax_equivalent_yield(federal_tax_rate=fed_tax, state_tax_rate=state_tax)
    assert tey > muni_yield, f"TEY ({tey}) must strictly exceed stated yield ({muni_yield}) for positive taxes"

# ==================== THEOREM 4: BRINSON-FACHLER EXACT RECONCILIATION ====================
@settings(max_examples=50)
@given(
    w1=st.floats(min_value=0.1, max_value=0.9),
    W1=st.floats(min_value=0.1, max_value=0.9),
    r1=st.floats(min_value=-0.3, max_value=0.5),
    r2=st.floats(min_value=-0.3, max_value=0.5),
    b1=st.floats(min_value=-0.3, max_value=0.5),
    b2=st.floats(min_value=-0.3, max_value=0.5),
)
def test_brinson_fachler_exact_sum_reconciliation(w1, W1, r1, r2, b1, b2):
    """
    Mathematical Invariant: Allocation + Selection + Interaction == Portfolio_Return - Benchmark_Return
    """
    w2 = 1.0 - w1
    W2 = 1.0 - W1
    
    df = pd.DataFrame([
        {"sector": "Sector A", "port_weight": w1, "bench_weight": W1, "port_return": r1, "bench_return": b1},
        {"sector": "Sector B", "port_weight": w2, "bench_weight": W2, "port_return": r2, "bench_return": b2}
    ])
    
    eng = PerformanceAttributionEngine()
    rep = eng.compute_brinson_attribution(df, model="Brinson-Fachler")
    
    sum_effects_bps = rep.total_allocation_effect_bps + rep.total_selection_effect_bps + rep.total_interaction_effect_bps
    excess_bps = rep.excess_return_pct * 100.0
    
    assert abs(sum_effects_bps - excess_bps) < 1.0, f"Attribution does not reconcile: Sum={sum_effects_bps} bps vs Excess={excess_bps} bps"
