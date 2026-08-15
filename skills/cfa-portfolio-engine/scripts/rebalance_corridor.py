#!/usr/bin/env python3
"""
CFA Portfolio Management: Optimal Rebalancing Corridor Calculator
Calculates optimal corridor widths [Target - w, Target + w] based on asset volatility,
transaction costs, risk tolerance, and tax consequences.
"""

import sys
import json

def calculate_rebalance_corridor(
    target_weight: float,
    volatility: float,
    transaction_cost_pct: float,
    tax_rate: float,
    risk_tolerance: str = "moderate",
    correlation_with_portfolio: float = 0.5
) -> dict:
    """
    CFA Level III Rebalancing Rules:
    - Higher Volatility -> NARROWER corridor (to keep risk in check)
    - Higher Transaction Costs -> WIDER corridor (to avoid excessive trading friction)
    - Higher Tax Rates -> WIDER corridor (to defer realized gains)
    - Higher Risk Tolerance -> WIDER corridor
    - Higher Correlation with rest of portfolio -> WIDER corridor (since assets move together)
    """
    base_corridor = 0.05  # 5% base width
    
    # Cost factor (Higher cost -> wider corridor)
    cost_multiplier = 1.0 + (transaction_cost_pct * 10)
    
    # Tax factor (Higher taxes -> wider corridor)
    tax_multiplier = 1.0 + (tax_rate * 0.8)
    
    # Volatility factor (Higher volatility -> narrower corridor)
    vol_multiplier = 1.0 / (1.0 + (volatility * 2.0))
    
    # Risk tolerance multiplier
    risk_multipliers = {"low": 0.7, "moderate": 1.0, "high": 1.3}
    risk_mult = risk_multipliers.get(risk_tolerance.lower(), 1.0)
    
    # Correlation factor (Higher correlation -> wider corridor)
    corr_multiplier = 1.0 + (correlation_with_portfolio * 0.3)
    
    optimal_half_width = base_corridor * cost_multiplier * tax_multiplier * vol_multiplier * risk_mult * corr_multiplier
    optimal_half_width = max(0.015, min(0.12, optimal_half_width))  # Cap between 1.5% and 12%
    
    lower_bound = max(0.0, target_weight - optimal_half_width)
    upper_bound = min(1.0, target_weight + optimal_half_width)
    
    return {
        "target_weight": round(target_weight, 4),
        "optimal_half_width": round(optimal_half_width, 4),
        "rebalance_trigger_lower": round(lower_bound, 4),
        "rebalance_trigger_upper": round(upper_bound, 4),
        "factors_analyzed": {
            "volatility": volatility,
            "transaction_cost_pct": transaction_cost_pct,
            "tax_rate": tax_rate,
            "risk_tolerance": risk_tolerance,
            "correlation_with_portfolio": correlation_with_portfolio
        }
    }

if __name__ == "__main__":
    result = calculate_rebalance_corridor(
        target_weight=0.30,
        volatility=0.20,
        transaction_cost_pct=0.005,
        tax_rate=0.25,
        risk_tolerance="moderate",
        correlation_with_portfolio=0.4
    )
    print(json.dumps(result, indent=2))
