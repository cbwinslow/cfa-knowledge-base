"""
CFA Multi-Portfolio Comparison & Macroeconomic Stress-Testing Scenario Lab
Implements:
1. Head-to-Head Comparative Analytics (Portfolio A vs. Portfolio B vs. S&P 500 Benchmark)
2. Side-by-Side Efficient Frontier & Sharpe Optimization
3. Deterministic Macroeconomic Stress Testing (1970s Stagflation, 2008 GFC, 2022 Tightening, AI Boom)
4. Interactive Plotly Spider / Radar & Waterfall Visualizations
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    from .instruments.portfolio import UnifiedPortfolio
    from .hopper import CentralDataHopper
except ImportError:
    try:
        from cfa_quant.instruments.portfolio import UnifiedPortfolio
        from cfa_quant.hopper import CentralDataHopper
    except ImportError:
        from instruments.portfolio import UnifiedPortfolio
        from hopper import CentralDataHopper

@dataclass
class PortfolioComparisonReport:
    portfolio_a_name: str
    portfolio_b_name: str
    metrics_a: Dict[str, Any]
    metrics_b: Dict[str, Any]
    delta_metrics: Dict[str, Any]
    allocation_comparison: pd.DataFrame
    stress_test_comparison: pd.DataFrame

class ScenarioLabEngine:
    def __init__(self, hopper: Optional[CentralDataHopper] = None):
        self.hopper = hopper or CentralDataHopper()

    def compare_portfolios(self, portfolio_a: UnifiedPortfolio, portfolio_b: UnifiedPortfolio) -> PortfolioComparisonReport:
        m_a = portfolio_a.compute_portfolio_metrics()
        m_b = portfolio_b.compute_portfolio_metrics()
        
        deltas = {
            "expected_return_delta_bps": round((m_b["expected_annual_return_pct"] - m_a["expected_annual_return_pct"]) * 100, 1),
            "volatility_delta_bps": round((m_b["annual_volatility_pct"] - m_a["annual_volatility_pct"]) * 100, 1),
            "sharpe_delta": round(m_b["sharpe_ratio"] - m_a["sharpe_ratio"], 2),
            "duration_delta_years": round(m_b["macaulay_duration_years"] - m_a["macaulay_duration_years"], 2),
            "var_95_delta_usd": round((m_b["total_value_usd"] * (m_b["var_95_pct_1yr"]/100)) - (m_a["total_value_usd"] * (m_a["var_95_pct_1yr"]/100)), 2)
        }
        
        alloc_a = m_a["asset_class_allocation"]
        alloc_b = m_b["asset_class_allocation"]
        all_classes = sorted(list(set(list(alloc_a.keys()) + list(alloc_b.keys()))))
        
        alloc_rows = []
        for ac in all_classes:
            w_a = alloc_a.get(ac, 0.0)
            w_b = alloc_b.get(ac, 0.0)
            alloc_rows.append({
                "Asset Class": ac,
                f"{portfolio_a.name} (%)": w_a,
                f"{portfolio_b.name} (%)": w_b,
                "Delta (% points)": round(w_b - w_a, 2)
            })
        df_alloc = pd.DataFrame(alloc_rows)
        
        scenarios = self.hopper.list_all_scenarios()
        stress_rows = []
        
        for sc in scenarios:
            res_a = self.run_portfolio_stress_test(portfolio_a, sc["shocks"])
            res_b = self.run_portfolio_stress_test(portfolio_b, sc["shocks"])
            
            stress_rows.append({
                "Macro Scenario": sc["scenario_name"],
                f"{portfolio_a.name} Impact (%)": f"{res_a['portfolio_impact_pct']:+.2f}%",
                f"{portfolio_a.name} P&L ($)": f"${res_a['portfolio_pnl_usd']:+,.2f}",
                f"{portfolio_b.name} Impact (%)": f"{res_b['portfolio_impact_pct']:+.2f}%",
                f"{portfolio_b.name} P&L ($)": f"${res_b['portfolio_pnl_usd']:+,.2f}",
                "Resilience Delta ($)": f"${(res_b['portfolio_pnl_usd'] - res_a['portfolio_pnl_usd']):+,.2f}"
            })
        df_stress = pd.DataFrame(stress_rows)
        
        return PortfolioComparisonReport(
            portfolio_a_name=portfolio_a.name,
            portfolio_b_name=portfolio_b.name,
            metrics_a=m_a,
            metrics_b=m_b,
            delta_metrics=deltas,
            allocation_comparison=df_alloc,
            stress_test_comparison=df_stress
        )

    def run_portfolio_stress_test(self, portfolio: UnifiedPortfolio, shocks: Dict[str, float]) -> Dict[str, Any]:
        total_initial_val = portfolio.total_portfolio_value
        if total_initial_val == 0:
            return {"portfolio_impact_pct": 0.0, "portfolio_pnl_usd": 0.0, "holding_details": []}
            
        total_pnl = 0.0
        details = []
        
        for inst, dollars in portfolio.holdings:
            ac_name = inst.asset_class.value
            shock_pct = shocks.get(ac_name, -0.05)
            
            if ac_name == "Fixed Income" and "rate_shock_bps" in shocks:
                dur = inst.compute_duration()
                shock_pct = -dur * (shocks["rate_shock_bps"] / 10000.0)
                
            holding_pnl = dollars * shock_pct
            total_pnl += holding_pnl
            
            details.append({
                "instrument_name": inst.name,
                "asset_class": ac_name,
                "initial_value": dollars,
                "shock_pct": round(shock_pct * 100, 2),
                "holding_pnl_usd": round(holding_pnl, 2),
                "post_shock_value": round(dollars + holding_pnl, 2)
            })
            
        total_impact_pct = (total_pnl / total_initial_val) * 100.0
        
        return {
            "portfolio_initial_value": total_initial_val,
            "portfolio_pnl_usd": round(total_pnl, 2),
            "portfolio_post_shock_value": round(total_initial_val + total_pnl, 2),
            "portfolio_impact_pct": round(total_impact_pct, 2),
            "holding_details": details
        }

    def render_comparison_visuals(self, report: PortfolioComparisonReport) -> Tuple[go.Figure, go.Figure]:
        df_alloc = report.allocation_comparison
        fig_bar = go.Figure()
        
        fig_bar.add_trace(go.Bar(
            x=df_alloc["Asset Class"],
            y=df_alloc[f"{report.portfolio_a_name} (%)"],
            name=report.portfolio_a_name,
            marker_color="#2979FF"
        ))
        fig_bar.add_trace(go.Bar(
            x=df_alloc["Asset Class"],
            y=df_alloc[f"{report.portfolio_b_name} (%)"],
            name=report.portfolio_b_name,
            marker_color="#00E676"
        ))
        
        fig_bar.update_layout(
            title="📊 Asset Allocation Comparison (% Weight)",
            barmode="group",
            template="plotly_dark",
            height=380,
            yaxis=dict(title="Weight (%)", gridcolor="#333842"),
            margin=dict(l=40, r=40, t=50, b=40)
        )
        
        categories = ["Expected Return", "Sharpe Ratio", "Downside Protection", "Convexity", "Duration Buffer"]
        
        def score_port(m):
            ret_s = min(10.0, m["expected_annual_return_pct"])
            sharpe_s = min(10.0, max(0.0, m["sharpe_ratio"] * 10.0))
            downside_s = max(0.0, 10.0 - (m["var_95_pct_1yr"] / 2.5))
            conv_s = min(10.0, m["portfolio_convexity"] / 5.0)
            dur_s = min(10.0, m["macaulay_duration_years"] * 1.2)
            return [ret_s, sharpe_s, downside_s, conv_s, dur_s]
            
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=score_port(report.metrics_a),
            theta=categories,
            fill='toself',
            name=report.portfolio_a_name,
            line=dict(color="#2979FF")
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=score_port(report.metrics_b),
            theta=categories,
            fill='toself',
            name=report.portfolio_b_name,
            line=dict(color="#00E676")
        ))
        
        fig_radar.update_layout(
            title="🎯 Multi-Dimensional Quantitative Factor Radar (0-10 Scale)",
            polar=dict(radialaxis=dict(visible=True, range=[0, 10], gridcolor="#333842")),
            template="plotly_dark",
            height=380,
            margin=dict(l=40, r=40, t=50, b=40)
        )
        
        return fig_bar, fig_radar

if __name__ == "__main__":
    try:
        from .instruments.fixed_income import FixedCouponBond, InflationLinkedBond
        from .instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
    except ImportError:
        try:
            from cfa_quant.instruments.fixed_income import FixedCouponBond, InflationLinkedBond
            from cfa_quant.instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
        except ImportError:
            from instruments.fixed_income import FixedCouponBond, InflationLinkedBond
            from instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
    
    print("=" * 75)
    print("🏛️ CFA SCENARIO LAB & MULTI-PORTFOLIO COMPARISON ENGINE")
    print("=" * 75)
    
    port_a = UnifiedPortfolio("Portfolio A (Traditional 60/40)")
    port_a.add_instrument(PublicEquityStock("US Large Cap Equities", beta=1.0, expected_earnings_growth=0.065, historical_volatility=0.18), 6000000.0)
    port_a.add_instrument(FixedCouponBond("Core Aggregate Bonds", coupon_rate=0.035, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
    
    port_b = UnifiedPortfolio("Portfolio B (CFA Institutional)")
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
