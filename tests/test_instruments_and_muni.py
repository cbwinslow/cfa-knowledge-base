"""
Unit & Edge-Case Tests for Multi-Asset Instruments, Muni Bonds, and Derivatives
"""

import pytest
from cfa_quant.instruments.fixed_income import FixedCouponBond, ZeroCouponBond, InflationLinkedBond
from cfa_quant.instruments.muni_and_structured import MunicipalBond, MortgageBackedSecurity
from cfa_quant.instruments.derivatives_fx import InterestRateSwap, ForexForward, EquityIndexFutures

def test_fixed_coupon_bond_par_discount_premium():
    # Par Bond (Coupon = YTM)
    par_bond = FixedCouponBond("ParBond", coupon_rate=0.05, maturity_years=10.0, yield_to_maturity=0.05, par_value=1000.0)
    assert abs(par_bond.compute_bond_price() - 1000.0) < 0.10, "Par bond price must equal par value"
    
    # Discount Bond (Coupon < YTM)
    disc_bond = FixedCouponBond("DiscBond", coupon_rate=0.03, maturity_years=10.0, yield_to_maturity=0.05, par_value=1000.0)
    assert disc_bond.compute_bond_price() < 1000.0, "Discount bond price must be below par"
    
    # Premium Bond (Coupon > YTM)
    prem_bond = FixedCouponBond("PremBond", coupon_rate=0.07, maturity_years=10.0, yield_to_maturity=0.05, par_value=1000.0)
    assert prem_bond.compute_bond_price() > 1000.0, "Premium bond price must be above par"

def test_municipal_bond_dscr_and_krd():
    muni = MunicipalBond(
        name="Airport Revenue Bond",
        muni_type="Revenue",
        coupon_rate=0.05,
        maturity_years=10.0,
        yield_to_maturity=0.035,
        annual_net_operating_revenue=30000000.0,
        annual_debt_service_due=15000000.0
    )
    
    dscr = muni.compute_debt_service_coverage_ratio()
    assert dscr == 2.0, f"Expected DSCR of 2.0x, got {dscr}"
    
    krds = muni.compute_key_rate_durations()
    assert "KRD_10Y" in krds and krds["KRD_10Y"] > 0, "10Y Bond should have positive 10Y Key Rate Duration"

def test_agency_mbs_negative_convexity():
    mbs = MortgageBackedSecurity("AgencyMBS", benchmark_psa_speed=150.0)
    
    # Faster PSA speed means higher CPR
    cpr = mbs.compute_cpr_prepayment_rate()
    assert cpr == (0.06 * 1.5), f"Expected 9.0% CPR at 150 PSA, got {cpr*100}%"
    assert mbs.compute_convexity() < 0.0, "MBS must exhibit negative convexity"

def test_interest_rate_swap_payer_vs_receiver():
    payer_swap = InterestRateSwap("PayerSwap", notional_principal=10000000.0, maturity_years=5.0, is_payer=True)
    receiver_swap = InterestRateSwap("ReceiverSwap", notional_principal=10000000.0, maturity_years=5.0, is_payer=False)
    
    # Payer swap duration is negative (hedges falling bond prices / rising rates)
    assert payer_swap.compute_duration() < 0.0, "Payer swap duration must be negative"
    # Receiver swap duration is positive
    assert receiver_swap.compute_duration() > 0.0, "Receiver swap duration must be positive"
    assert payer_swap.compute_duration() == -receiver_swap.compute_duration(), "Payer and Receiver durations must be mirror opposites"
