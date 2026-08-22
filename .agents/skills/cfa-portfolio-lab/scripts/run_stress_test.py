#!/usr/bin/env python3
"""
CLI Script for CFA Portfolio Comparison and Macro Stress Testing Lab
"""

import sys
import json
from pathlib import Path

# Ensure root in path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cfa_quant.instruments.portfolio import UnifiedPortfolio
from cfa_quant.instruments.fixed_income import FixedCouponBond, InflationLinkedBond
from cfa_quant.instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
from cfa_quant.scenario_lab import ScenarioLabEngine

def main():
    print("=" * 75)
    print("🏛️ AUTONOMOUS CFA PORTFOLIO COMPARISON & STRESS-TEST LAB")
    print("=" * 75)
    
    # Portfolio A: Traditional 60/40 Portfolio ($10M)
    port_a = UnifiedPortfolio("Portfolio A (Current 60/40)")
    port_a.add_instrument(PublicEquityStock("US Large Cap Equities", beta=1.0, expected_earnings_growth=0.065, historical_volatility=0.18), 6000000.0)
    port_a.add_instrument(FixedCouponBond("Core Aggregate Bonds", coupon_rate=0.035, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
    
    # Portfolio B: Proposed Institutional Endowment Portfolio ($10M)
    port_b = UnifiedPortfolio("Portfolio B (Proposed Institutional SAA)")
    port_b.add_instrument(PublicEquityStock("Global Compounders", beta=0.95, expected_earnings_growth=0.08, historical_volatility=0.16), 4000000.0)
    port_b.add_instrument(FixedCouponBond("10Y Treasury LDI", coupon_rate=0.045, maturity_years=10.0, yield_to_maturity=0.0469), 2000000.0)
    port_b.add_instrument(InflationLinkedBond("10Y TIPS Inflation Hedge", coupon_rate=0.020, maturity_years=10.0, yield_to_maturity=0.021), 1500000.0)
    port_b.add_instrument(RealEstateAsset("Commercial Real Estate", net_operating_income=80000.0, cap_rate=0.055), 1500000.0)
    port_b.add_instrument(PrivateEquityHolding("Growth Equity LP", target_irr=0.15), 1000000.0)
    
    lab = ScenarioLabEngine()
    report = lab.compare_portfolios(port_a, port_b)
    
    print(f"Portfolio A Return: {report.metrics_a['expected_annual_return_pct']}% | Vol: {report.metrics_a['annual_volatility_pct']}% | Sharpe: {report.metrics_a['sharpe_ratio']}")
    print(f"Portfolio B Return: {report.metrics_b['expected_annual_return_pct']}% | Vol: {report.metrics_b['annual_volatility_pct']}% | Sharpe: {report.metrics_b['sharpe_ratio']}")
    print(f"Expected Return Delta: {report.delta_metrics['expected_return_delta_bps']:+0.1f} bps | Sharpe Delta: {report.delta_metrics['sharpe_delta']:+0.2f}")
    
    print("\n⚡ Macroeconomic Stress Test Comparison:")
    print(report.stress_test_comparison.to_string(index=False))
    print("=" * 75)

if __name__ == "__main__":
    main()
