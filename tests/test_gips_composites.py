"""
Unit, Negative, Boundary & Mathematical Invariant Tests for GIPS Composite Reporting Engine
"""

import pytest
import numpy as np
from cfa_quant.portfolio_risk.gips_composites import GipsCompositeEngine

def test_modified_dietz_and_twrr_exactness():
    # BMV = $1,000,000, EMV = $1,280,000, CF = $200,000 on day 10 of 30
    # Day weight W = (30 - 10) / 30 = 2/3
    # Weighted CF = 200,000 * (2/3) = 133,333.33
    # Denominator = 1,000,000 + 133,333.33 = 1,133,333.33
    # Numerator = 1,280,000 - 1,000,000 - 200,000 = 80,000
    # Expected R_md = 80,000 / 1,133,333.33 = 7.0588%
    
    r_md = GipsCompositeEngine.calculate_modified_dietz_return(
        beginning_market_value=1000000.0,
        ending_market_value=1280000.0,
        cash_flows=[(200000.0, 10)],
        total_days_in_period=30
    )
    assert abs(r_md - 0.070588) < 1e-4
    
    # Test True Daily TWRR: (1 + 0.02) * (1 - 0.01) * (1 + 0.03) - 1 = 4.0094%
    twrr = GipsCompositeEngine.calculate_daily_twrr([0.02, -0.01, 0.03])
    expected_twrr = (1.02 * 0.99 * 1.03) - 1.0
    assert abs(twrr - expected_twrr) < 1e-6

def test_gips_composite_aggregation_and_dispersion():
    engine = GipsCompositeEngine("TEST_LARGE_CAP_COMPOSITE")
    
    # Add 6 portfolios
    ports = [
        ("PORT_1", 1000000.0, 1100000.0, 0.10),
        ("PORT_2", 2000000.0, 2240000.0, 0.12),
        ("PORT_3", 3000000.0, 3420000.0, 0.14),
        ("PORT_4", 1500000.0, 1665000.0, 0.11),
        ("PORT_5", 2500000.0, 2825000.0, 0.13),
        ("PORT_6", 1000000.0, 1090000.0, 0.09)
    ]
    for pid, bmv, emv, r_g in ports:
        engine.add_portfolio_period_data(pid, bmv, emv, gross_return=r_g, annual_fee_bps=60.0)
        
    res = engine.compute_composite_annual_performance(benchmark_annual_return=0.09, total_firm_assets=50000000.0)
    p = res["presentation"]
    
    assert res["status"] == "success"
    assert p["number_of_portfolios"] == 6
    assert p["composite_gross_return_pct"] > p["composite_net_return_pct"]  # Gross >= Net invariant
    assert p["composite_gross_return_pct"] > p["benchmark_return_pct"]
    assert p["gross_excess_return_pct"] > 0.0
    assert p["internal_dispersion_std_pct"] != "N/A (<5 ports)"
    assert res["dispersion_details"]["high_low_spread"] == pytest.approx(0.05, abs=1e-4) # 0.14 - 0.09 = 0.05

def test_non_discretionary_exclusion_and_empty_composite():
    engine = GipsCompositeEngine("TEST_DISCRETIONARY_ONLY")
    
    # 1. Non-discretionary account should be excluded from composite per GIPS standard
    engine.add_portfolio_period_data("NON_DISC_1", 5000000.0, 5500000.0, 0.10, is_discretionary=False)
    assert len(engine.portfolios) == 0
    
    # 2. Empty composite handles gracefully
    empty_res = engine.compute_composite_annual_performance()
    assert empty_res["status"] == "error"
