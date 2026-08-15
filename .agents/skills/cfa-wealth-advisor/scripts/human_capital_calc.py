#!/usr/bin/env python3
"""
CFA Private Wealth Management: Human Capital & Economic Balance Sheet Calculator
Computes Human Capital (PV of mortality-weighted future wages) and Holistic Asset Allocation.
"""

import sys
import json

def calculate_human_capital(
    current_age: int,
    retirement_age: int,
    annual_income: float,
    wage_growth_rate: float,
    discount_rate: float,
    annual_survival_prob: float = 0.99
) -> float:
    """
    Calculates Human Capital:
    HC_0 = sum_{t=1}^{N} [ (Prob_t * Wage_{t-1} * (1 + g)) / (1 + r)^t ]
    """
    hc = 0.0
    current_wage = annual_income
    cumulative_survival = 1.0
    
    for t in range(1, retirement_age - current_age + 1):
        current_wage *= (1 + wage_growth_rate)
        cumulative_survival *= annual_survival_prob
        pv_year = (cumulative_survival * current_wage) / ((1 + discount_rate) ** t)
        hc += pv_year
        
    return hc

def holistic_asset_allocation(
    financial_capital: float,
    human_capital: float,
    hc_nature: str,  # 'bond_like' or 'equity_like'
    target_overall_equity_weight: float = 0.60
):
    """
    Allocates Financial Capital taking into account the asset character of Human Capital.
    """
    total_wealth = financial_capital + human_capital
    desired_equity_dollars = total_wealth * target_overall_equity_weight
    
    # Human capital equity equivalent
    hc_equity_pct = 0.15 if hc_nature == "bond_like" else 0.70
    hc_equity_dollars = human_capital * hc_equity_pct
    
    # Remaining equity needed from financial capital
    fc_equity_dollars = max(0.0, desired_equity_dollars - hc_equity_dollars)
    fc_equity_dollars = min(financial_capital, fc_equity_dollars)
    fc_bond_dollars = financial_capital - fc_equity_dollars
    
    return {
        "total_economic_wealth": round(total_wealth, 2),
        "human_capital": round(human_capital, 2),
        "financial_capital": round(financial_capital, 2),
        "fc_equity_weight": round(fc_equity_dollars / financial_capital, 4),
        "fc_bond_weight": round(fc_bond_dollars / financial_capital, 4),
        "fc_equity_dollars": round(fc_equity_dollars, 2),
        "fc_bond_dollars": round(fc_bond_dollars, 2)
    }

if __name__ == "__main__":
    # Example demo run
    hc = calculate_human_capital(
        current_age=35,
        retirement_age=65,
        annual_income=150000,
        wage_growth_rate=0.03,
        discount_rate=0.05
    )
    result = holistic_asset_allocation(
        financial_capital=500000,
        human_capital=hc,
        hc_nature="bond_like",
        target_overall_equity_weight=0.60
    )
    print(json.dumps(result, indent=2))
