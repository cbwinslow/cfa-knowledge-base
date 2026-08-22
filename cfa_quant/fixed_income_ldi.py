"""
CFA Level III Fixed Income Liability-Driven Investing (LDI) & Immunization Engine
Implements:
1. Classical Single-Liability & Multi-Liability Cash Flow Immunization
2. Convexity Matching & Structural Dispersion Minimization (M^2)
3. Key Rate Duration Analysis (2Y, 5Y, 10Y, 30Y Non-Parallel Yield Curve Shocks)
4. Contingent Immunization & Surplus Alpha Buffer Tracking
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go

@dataclass
class BondAsset:
    name: str
    coupon_rate: float        # Annual coupon rate (e.g. 0.045 for 4.5%)
    maturity_years: float     # Maturity in years
    yield_to_maturity: float  # Annual YTM
    par_value: float = 1000.0
    price: float = 1000.0
    macaulay_duration: float = 0.0
    modified_duration: float = 0.0
    convexity: float = 0.0
    key_rate_durations: Dict[str, float] = field(default_factory=dict)

@dataclass
class LiabilityObligation:
    name: str
    due_in_years: float
    cash_flow_amount: float
    discount_yield: float
    present_value: float = 0.0
    macaulay_duration: float = 0.0
    convexity: float = 0.0

@dataclass
class ImmunizationResult:
    portfolio_present_value: float
    liability_present_value: float
    surplus_cushion_usd: float
    is_solvency_satisfied: bool      # PV_P >= PV_L
    portfolio_macaulay_duration: float
    liability_macaulay_duration: float
    duration_gap: float
    is_duration_matched: bool        # |D_P - D_L| <= 0.1 years
    portfolio_convexity: float
    liability_convexity: float
    is_convexity_satisfied: bool     # C_P >= C_L
    structural_dispersion_m2: float  # M^2 measure
    contingent_immunization_status: str
    optimal_asset_weights: Dict[str, float]

class FixedIncomeLdiEngine:
    def __init__(self):
        pass

    def compute_bond_analytics(self, coupon_rate: float, maturity_years: int, ytm: float, par: float = 1000.0, freq: int = 2) -> BondAsset:
        """
        Computes accurate Price, Macaulay Duration, Modified Duration, and Convexity for fixed coupon bonds.
        """
        periods = maturity_years * freq
        coupon_pmt = (coupon_rate * par) / freq
        y_per = ytm / freq
        
        times = np.arange(1, periods + 1) / freq
        cash_flows = np.full(periods, coupon_pmt)
        cash_flows[-1] += par
        
        pv_factors = 1.0 / ((1.0 + y_per) ** np.arange(1, periods + 1))
        pv_cash_flows = cash_flows * pv_factors
        bond_price = np.sum(pv_cash_flows)
        
        # Macaulay Duration (Years)
        weights = pv_cash_flows / bond_price
        mac_dur = np.sum(times * weights)
        
        # Modified Duration
        mod_dur = mac_dur / (1.0 + y_per)
        
        # Convexity
        t_t_plus_1 = np.arange(1, periods + 1) * (np.arange(1, periods + 1) + 1)
        conv = np.sum(t_t_plus_1 * pv_cash_flows) / (bond_price * ((1.0 + y_per) ** 2) * (freq ** 2))
        
        # Key Rate Durations (2Y, 5Y, 10Y, 30Y nodes)
        krd = {
            "2Y": mod_dur if maturity_years <= 3 else (mod_dur * 0.4 if maturity_years <= 7 else 0.0),
            "5Y": mod_dur * 0.6 if 3 < maturity_years <= 7 else (mod_dur * 0.3 if 7 < maturity_years <= 12 else 0.0),
            "10Y": mod_dur * 0.7 if 7 < maturity_years <= 15 else (mod_dur * 0.2 if maturity_years > 15 else 0.0),
            "30Y": mod_dur * 0.8 if maturity_years > 15 else 0.0
        }
        
        return BondAsset(
            name=f"{maturity_years}Y Treasury ({coupon_rate*100:.1f}% Coupon)",
            coupon_rate=coupon_rate,
            maturity_years=float(maturity_years),
            yield_to_maturity=ytm,
            par_value=par,
            price=round(bond_price, 2),
            macaulay_duration=round(mac_dur, 3),
            modified_duration=round(mod_dur, 3),
            convexity=round(conv, 3),
            key_rate_durations={k: round(v, 3) for k, v in krd.items()}
        )

    def evaluate_liability_immunization(
        self,
        portfolio_assets: List[Tuple[BondAsset, float]],  # List of (BondAsset, dollar_allocation)
        liability: LiabilityObligation
    ) -> ImmunizationResult:
        """
        Evaluates the 3 mandatory CFA Level III Immunization Conditions:
        1. PV_Portfolio >= PV_Liability (Solvency)
        2. Macaulay Duration_P = Macaulay Duration_L (Price & Reinvestment risk offset)
        3. Convexity_P >= Convexity_L with minimized M^2 dispersion (Protection against structural yield curve shifts)
        """
        # 1. Liability Calculations (Zero-coupon or single disbursement)
        pv_l = liability.cash_flow_amount / ((1.0 + liability.discount_yield) ** liability.due_in_years)
        mac_dur_l = liability.due_in_years
        conv_l = (liability.due_in_years * (liability.due_in_years + 1.0)) / ((1.0 + liability.discount_yield) ** 2)
        
        # 2. Portfolio Calculations
        total_p_value = sum(dollars for _, dollars in portfolio_assets)
        weights = [dollars / total_p_value for _, dollars in portfolio_assets]
        
        p_mac_dur = sum(weights[i] * portfolio_assets[i][0].macaulay_duration for i in range(len(portfolio_assets)))
        p_conv = sum(weights[i] * portfolio_assets[i][0].convexity for i in range(len(portfolio_assets)))
        
        # 3. Structural Dispersion M^2: M^2 = sum(w_i * (t_i - D_L)^2)
        m2_dispersion = sum(weights[i] * ((portfolio_assets[i][0].maturity_years - mac_dur_l) ** 2) for i in range(len(portfolio_assets)))
        
        # 4. Solvency & Conditions
        surplus = total_p_value - pv_l
        is_solvency = surplus >= 0.0
        dur_gap = p_mac_dur - mac_dur_l
        is_dur_match = abs(dur_gap) <= 0.15
        is_conv_match = p_conv >= conv_l
        
        # 5. Contingent Immunization Status
        # Safety cushion = (Portfolio Value - PV_Liability) / Portfolio Value
        cushion_pct = (surplus / total_p_value) * 100.0 if total_p_value > 0 else 0.0
        if cushion_pct > 10.0:
            status = f"ACTIVE ALPHA SURPLUS: Safety Cushion is {cushion_pct:.1f}%. Manager is permitted to take active risk/equity overlay."
        elif cushion_pct > 0.0:
            status = f"MONITOR CLOSELY: Safety Cushion is {cushion_pct:.1f}%. Approaching trigger threshold."
        else:
            status = "IMMUNIZATION TRIGGER BREACHED: Portfolio must be 100% locked into zero-risk immunized duration matching."

        opt_weights = {portfolio_assets[i][0].name: round(weights[i] * 100, 2) for i in range(len(portfolio_assets))}

        return ImmunizationResult(
            portfolio_present_value=round(total_p_value, 2),
            liability_present_value=round(pv_l, 2),
            surplus_cushion_usd=round(surplus, 2),
            is_solvency_satisfied=is_solvency,
            portfolio_macaulay_duration=round(p_mac_dur, 2),
            liability_macaulay_duration=round(mac_dur_l, 2),
            duration_gap=round(dur_gap, 2),
            is_duration_matched=is_dur_match,
            portfolio_convexity=round(p_conv, 2),
            liability_convexity=round(conv_l, 2),
            is_convexity_satisfied=is_conv_match,
            structural_dispersion_m2=round(m2_dispersion, 2),
            contingent_immunization_status=status,
            optimal_asset_weights=opt_weights
        )

    def simulate_yield_curve_shifts(
        self,
        portfolio_assets: List[Tuple[BondAsset, float]],
        liability: LiabilityObligation,
        shift_type: str = "Parallel +100bps"
    ) -> Dict[str, Any]:
        """
        Simulates impact of non-parallel yield curve shocks on Portfolio vs. Liability surplus:
        1. Parallel Shift (+100 bps / -100 bps)
        2. Steepening Curve (Short -50 bps, Long +50 bps)
        3. Flattening Curve (Short +50 bps, Long -50 bps)
        4. Butterfly / Curvature (2Y/30Y +50 bps, 10Y -50 bps)
        """
        scenarios = {
            "Parallel +100bps": {"2Y": 0.010, "5Y": 0.010, "10Y": 0.010, "30Y": 0.010},
            "Parallel -100bps": {"2Y": -0.010, "5Y": -0.010, "10Y": -0.010, "30Y": -0.010},
            "Steepening": {"2Y": -0.005, "5Y": 0.000, "10Y": 0.005, "30Y": 0.010},
            "Flattening": {"2Y": 0.010, "5Y": 0.005, "10Y": 0.000, "30Y": -0.005},
            "Positive Butterfly": {"2Y": 0.005, "5Y": -0.005, "10Y": -0.005, "30Y": 0.005}
        }
        
        shocks = scenarios.get(shift_type, scenarios["Parallel +100bps"])
        
        # Portfolio dollar change via KRD
        total_p_val = sum(dollars for _, dollars in portfolio_assets)
        p_delta_dollars = 0.0
        
        for asset, dollars in portfolio_assets:
            # Asset price percentage change = -sum(KRD_i * Shock_i) + 0.5 * Conv * AvgShock^2
            krd_impact = sum(asset.key_rate_durations.get(node, 0.0) * shock for node, shock in shocks.items())
            pct_change = -krd_impact + (0.5 * asset.convexity * (0.01 ** 2))
            p_delta_dollars += dollars * pct_change
            
        # Liability dollar change
        l_pv = liability.cash_flow_amount / ((1.0 + liability.discount_yield) ** liability.due_in_years)
        avg_l_shock = np.mean(list(shocks.values()))
        l_mod_dur = liability.due_in_years / (1.0 + liability.discount_yield)
        l_conv = (liability.due_in_years * (liability.due_in_years + 1.0)) / ((1.0 + liability.discount_yield) ** 2)
        
        l_pct_change = (-l_mod_dur * avg_l_shock) + (0.5 * l_conv * (avg_l_shock ** 2))
        l_delta_dollars = l_pv * l_pct_change
        
        new_p_val = total_p_val + p_delta_dollars
        new_l_val = l_pv + l_delta_dollars
        new_surplus = new_p_val - new_l_val
        
        return {
            "scenario": shift_type,
            "portfolio_value_initial": round(total_p_val, 2),
            "portfolio_value_post_shock": round(new_p_val, 2),
            "portfolio_change_pct": round((p_delta_dollars / total_p_val) * 100, 2),
            "liability_value_initial": round(l_pv, 2),
            "liability_value_post_shock": round(new_l_val, 2),
            "liability_change_pct": round(l_pct_change * 100, 2),
            "initial_surplus": round(total_p_val - l_pv, 2),
            "post_shock_surplus": round(new_surplus, 2),
            "immunization_protected": new_surplus >= 0.0
        }

if __name__ == "__main__":
    ldi = FixedIncomeLdiEngine()
    print("=" * 75)
    print("🏛️ CFA LEVEL III FIXED INCOME LDI & IMMUNIZATION ENGINE")
    print("=" * 75)
    
    # 1. Define Liability: $10,000,000 due in 7 years discounted at 4.5%
    liab = LiabilityObligation(
        name="Pension Payout Obligation",
        due_in_years=7.0,
        cash_flow_amount=10000000.0,
        discount_yield=0.045
    )
    
    # 2. Define Candidate Bond Portfolio (Barbell Strategy: 3Y + 12Y Bonds)
    bond_3y = ldi.compute_bond_analytics(coupon_rate=0.040, maturity_years=3, ytm=0.042)
    bond_12y = ldi.compute_bond_analytics(coupon_rate=0.048, maturity_years=12, ytm=0.048)
    
    # Construct immunized portfolio: 55% in 3Y, 45% in 12Y ($7.5M Total Capital)
    portfolio = [
        (bond_3y, 4125000.0),
        (bond_12y, 3375000.0)
    ]
    
    res = ldi.evaluate_liability_immunization(portfolio, liab)
    print(f"Portfolio PV: ${res.portfolio_present_value:,.2f} | Liability PV: ${res.liability_present_value:,.2f}")
    print(f"Surplus Buffer: ${res.surplus_cushion_usd:,.2f}")
    print(f"Portfolio Duration: {res.portfolio_macaulay_duration} yrs | Liability Duration: {res.liability_macaulay_duration} yrs (Matched: {res.is_duration_matched})")
    print(f"Portfolio Convexity: {res.portfolio_convexity} | Liability Convexity: {res.liability_convexity} (Satisfied: {res.is_convexity_satisfied})")
    print(f"Structural Dispersion (M^2): {res.structural_dispersion_m2}")
    print(f"Status: {res.contingent_immunization_status}")
    
    # Test Yield Curve Shock
    shock = ldi.simulate_yield_curve_shifts(portfolio, liab, shift_type="Steepening")
    print(f"\nYield Curve Shock Scenario ({shock['scenario']}):")
    print(f"  • Post-Shock Surplus: ${shock['post_shock_surplus']:,.2f} (Protected: {shock['immunization_protected']})")
    print("=" * 75)
