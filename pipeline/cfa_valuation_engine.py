#!/usr/bin/env python3
"""
CFA Multi-Stage Valuation Engine
Implements:
1. Dynamic WACC (CAPM + Cost of Debt)
2. 3-Stage FCFF Discounted Cash Flow Model
3. Residual Income Model (Clean Surplus / EVA)
4. Valuation Sensitivity Table (WACC vs. Perpetual Growth)
"""

import numpy as np
from typing import Dict, Any, List

EQUITY_RISK_PREMIUM = 0.050  # 5.0% Standard US Equity Risk Premium
PERPETUAL_GROWTH_RATE = 0.025 # 2.5% Long-term GDP perpetual growth

class CfaValuationEngine:
    def __init__(self, erp: float = EQUITY_RISK_PREMIUM, perpetual_growth: float = PERPETUAL_GROWTH_RATE):
        self.erp = erp
        self.perpetual_growth = perpetual_growth

    def compute_wacc(
        self,
        market_cap: float,
        total_debt: float,
        beta: float,
        risk_free_rate: float,
        effective_tax_rate: float = 0.21,
        cost_of_debt_spread: float = 0.015
    ) -> Dict[str, float]:
        """
        Calculates WACC = (E/V * r_e) + (D/V * r_d * (1 - t))
        """
        # Cost of Equity via CAPM
        cost_of_equity = risk_free_rate + (beta * self.erp)
        
        # Pre-tax Cost of Debt = Rf + Credit Spread
        cost_of_debt = risk_free_rate + cost_of_debt_spread
        after_tax_cost_of_debt = cost_of_debt * (1.0 - effective_tax_rate)
        
        total_firm_value = market_cap + total_debt
        if total_firm_value == 0:
            weight_equity = 1.0
            weight_debt = 0.0
        else:
            weight_equity = market_cap / total_firm_value
            weight_debt = total_debt / total_firm_value
            
        wacc = (weight_equity * cost_of_equity) + (weight_debt * after_tax_cost_of_debt)
        
        return {
            "wacc": round(wacc, 4),
            "cost_of_equity": round(cost_of_equity, 4),
            "cost_of_debt_pretax": round(cost_of_debt, 4),
            "cost_of_debt_aftertax": round(after_tax_cost_of_debt, 4),
            "weight_equity": round(weight_equity, 4),
            "weight_debt": round(weight_debt, 4)
        }

    def compute_3stage_dcf(
        self,
        latest_cfo: float,
        latest_capex: float,
        cash_and_equivalents: float,
        total_debt: float,
        shares_outstanding: int,
        wacc: float,
        growth_stage1: float = 0.10,
        years_stage1: int = 3,
        years_stage2: int = 4
    ) -> Dict[str, Any]:
        """
        3-Stage DCF:
        Stage 1: High growth (years 1 to years_stage1)
        Stage 2: Fade growth transitioning to perpetual_growth (years_stage1+1 to years_stage1+years_stage2)
        Stage 3: Perpetual Gordon Growth Terminal Value
        """
        base_fcff = max(0.0, latest_cfo - latest_capex)
        if base_fcff == 0:
            base_fcff = 1000000.0  # Fallback minimum
            
        projected_fcff = []
        current_fcff = base_fcff
        pv_forecast_cashflows = 0.0
        
        total_forecast_years = years_stage1 + years_stage2
        
        # Stage 1: High Growth
        for y in range(1, years_stage1 + 1):
            current_fcff *= (1.0 + growth_stage1)
            pv = current_fcff / ((1.0 + wacc) ** y)
            pv_forecast_cashflows += pv
            projected_fcff.append({"year": y, "fcff": current_fcff, "pv": pv, "growth": growth_stage1})
            
        # Stage 2: Linear Fade Growth to Perpetual Rate
        fade_step = (growth_stage1 - self.perpetual_growth) / (years_stage2 + 1)
        current_g = growth_stage1
        for y in range(years_stage1 + 1, total_forecast_years + 1):
            current_g -= fade_step
            current_fcff *= (1.0 + current_g)
            pv = current_fcff / ((1.0 + wacc) ** y)
            pv_forecast_cashflows += pv
            projected_fcff.append({"year": y, "fcff": current_fcff, "pv": pv, "growth": current_g})
            
        # Stage 3: Terminal Value at year total_forecast_years
        terminal_wacc = max(wacc, self.perpetual_growth + 0.01)
        terminal_value = (current_fcff * (1.0 + self.perpetual_growth)) / (terminal_wacc - self.perpetual_growth)
        pv_terminal_value = terminal_value / ((1.0 + wacc) ** total_forecast_years)
        
        enterprise_value = pv_forecast_cashflows + pv_terminal_value
        equity_value = enterprise_value + cash_and_equivalents - total_debt
        
        intrinsic_value_per_share = max(0.0, equity_value / max(shares_outstanding, 1))
        
        return {
            "base_fcff": round(base_fcff, 2),
            "pv_forecast_period": round(pv_forecast_cashflows, 2),
            "terminal_value": round(terminal_value, 2),
            "pv_terminal_value": round(pv_terminal_value, 2),
            "enterprise_value": round(enterprise_value, 2),
            "equity_value": round(equity_value, 2),
            "intrinsic_value_per_share": round(intrinsic_value_per_share, 2),
            "projected_cash_flows": projected_fcff
        }

    def compute_residual_income_model(
        self,
        latest_book_value: float,
        latest_net_income: float,
        cost_of_equity: float,
        shares_outstanding: int,
        forecast_roe: float = 0.15,
        forecast_years: int = 5,
        persistence_factor: float = 0.60
    ) -> Dict[str, Any]:
        """
        Residual Income (Clean Surplus / Edwards-Bell-Ohlson) Model:
        V_0 = B_0 + sum [ (ROE - r_e) * B_{t-1} / (1 + r_e)^t ] + Terminal RI
        """
        pv_ri_sum = 0.0
        current_bv = latest_book_value
        ri_projections = []
        
        for t in range(1, forecast_years + 1):
            expected_ni = current_bv * forecast_roe
            equity_charge = current_bv * cost_of_equity
            ri = expected_ni - equity_charge
            pv_ri = ri / ((1.0 + cost_of_equity) ** t)
            pv_ri_sum += pv_ri
            
            # Clean surplus book value reinvestment
            dividend_payout = expected_ni * 0.30
            current_bv += (expected_ni - dividend_payout)
            ri_projections.append({"year": t, "residual_income": ri, "pv": pv_ri})
            
        # Terminal Residual Income using persistence factor omega
        terminal_ri = (ri_projections[-1]["residual_income"] * persistence_factor) / (1.0 + cost_of_equity - persistence_factor)
        pv_terminal_ri = terminal_ri / ((1.0 + cost_of_equity) ** forecast_years)
        
        total_equity_value = latest_book_value + pv_ri_sum + pv_terminal_ri
        ri_per_share = max(0.0, total_equity_value / max(shares_outstanding, 1))
        
        return {
            "current_book_value": round(latest_book_value, 2),
            "pv_forecast_ri": round(pv_ri_sum, 2),
            "pv_terminal_ri": round(pv_terminal_ri, 2),
            "total_equity_value": round(total_equity_value, 2),
            "intrinsic_value_per_share": round(ri_per_share, 2)
        }

    def generate_sensitivity_matrix(
        self,
        base_cfo: float,
        base_capex: float,
        cash: float,
        debt: float,
        shares: int,
        base_wacc: float,
        growth_rate: float
    ) -> Dict[str, Any]:
        """
        Generates a 5x5 sensitivity matrix varying WACC and Perpetual Growth Rate.
        """
        wacc_range = [base_wacc - 0.015, base_wacc - 0.0075, base_wacc, base_wacc + 0.0075, base_wacc + 0.015]
        g_range = [self.perpetual_growth - 0.010, self.perpetual_growth - 0.005, self.perpetual_growth, self.perpetual_growth + 0.005, self.perpetual_growth + 0.010]
        
        matrix = []
        for w in wacc_range:
            row = []
            for g in g_range:
                if w <= g:
                    row.append(0.0)
                else:
                    self.perpetual_growth = g
                    res = self.compute_3stage_dcf(base_cfo, base_capex, cash, debt, shares, w, growth_stage1=growth_rate)
                    row.append(res["intrinsic_value_per_share"])
            matrix.append(row)
            
        self.perpetual_growth = PERPETUAL_GROWTH_RATE
        return {
            "wacc_axis": [round(w * 100, 2) for w in wacc_range],
            "growth_axis": [round(g * 100, 2) for g in g_range],
            "matrix": matrix
        }
