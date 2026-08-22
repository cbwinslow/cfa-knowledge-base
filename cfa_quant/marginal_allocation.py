"""
CFA Level III Marginal Allocation & Asset Addition Analysis Engine
Implements:
1. Incremental Portfolio Asset Addition Simulation (Before vs. After)
2. Marginal Contribution to Risk (MCTR) and Percentage Contribution to Risk (%CTR)
3. Diversification Benefit & Sharpe Ratio Gradient Analysis
4. 3D Risk-Return Landscape Generation
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import copy
import numpy as np
import pandas as pd
import plotly.graph_objects as go

try:
    from .instruments.base import InvestmentInstrument, AssetClass
    from .instruments.portfolio import UnifiedPortfolio
    from .visualization_suite import PortfolioVisualizer
except ImportError:
    try:
        from cfa_quant.instruments.base import InvestmentInstrument, AssetClass
        from cfa_quant.instruments.portfolio import UnifiedPortfolio
        from cfa_quant.visualization_suite import PortfolioVisualizer
    except ImportError:
        from instruments.base import InvestmentInstrument, AssetClass
        from instruments.portfolio import UnifiedPortfolio
        from visualization_suite import PortfolioVisualizer

@dataclass
class AdditionSimulationResult:
    candidate_instrument_name: str
    added_dollar_amount: float
    added_weight_pct: float
    correlation_with_portfolio: float
    
    metrics_before: Dict[str, Any]
    metrics_after: Dict[str, Any]
    delta_metrics: Dict[str, Any]
    
    mctr_contributions_pct: List[float]
    holdings_names_after: List[str]
    diversification_benefit_pct: float
    recommendation_verdict: str

class MarginalAllocationEngine:
    def __init__(self, visualizer: Optional[PortfolioVisualizer] = None):
        self.viz = visualizer or PortfolioVisualizer()

    def simulate_asset_addition(
        self,
        base_portfolio: UnifiedPortfolio,
        candidate_instrument: InvestmentInstrument,
        dollar_to_add: float,
        assumed_correlation_with_portfolio: float = 0.35
    ) -> Tuple[AdditionSimulationResult, go.Figure, go.Figure, go.Figure]:
        """
        Simulates the before-and-after impact of adding an investment instrument.
        """
        m_before = base_portfolio.compute_portfolio_metrics()
        
        port_after = UnifiedPortfolio(name=f"{base_portfolio.name} (+ {candidate_instrument.name})", risk_free_rate=base_portfolio.rf)
        for inst, dollars in base_portfolio.holdings:
            port_after.add_instrument(inst, dollars)
            
        port_after.add_instrument(candidate_instrument, dollar_to_add)
        m_after = port_after.compute_portfolio_metrics()
        
        total_after_val = port_after.total_portfolio_value
        added_weight = (dollar_to_add / total_after_val) * 100.0 if total_after_val > 0 else 0.0
        
        delta_ret_bps = (m_after["expected_annual_return_pct"] - m_before["expected_annual_return_pct"]) * 100.0
        delta_vol_bps = (m_after["annual_volatility_pct"] - m_before["annual_volatility_pct"]) * 100.0
        delta_sharpe = m_after["sharpe_ratio"] - m_before["sharpe_ratio"]
        delta_duration = m_after["macaulay_duration_years"] - m_before["macaulay_duration_years"]
        delta_var_usd = (m_after["total_value_usd"] * (m_after["var_95_pct_1yr"]/100.0)) - (m_before["total_value_usd"] * (m_before["var_95_pct_1yr"]/100.0))
        
        deltas = {
            "return_delta_bps": round(delta_ret_bps, 1),
            "volatility_delta_bps": round(delta_vol_bps, 1),
            "sharpe_delta": round(delta_sharpe, 2),
            "duration_delta_years": round(delta_duration, 2),
            "var_95_delta_usd": round(delta_var_usd, 2)
        }
        
        weights = np.array([d / total_after_val for _, d in port_after.holdings])
        volatilities = np.array([inst.compute_volatility() for inst, _ in port_after.holdings])
        
        n = len(port_after.holdings)
        corr_matrix = np.full((n, n), 0.35)
        np.fill_diagonal(corr_matrix, 1.0)
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix
        
        port_sd = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        mctr = np.dot(cov_matrix, weights) / port_sd
        pct_ctr = (weights * mctr) / port_sd
        pct_ctr_normalized = [round(float(p) * 100.0, 1) for p in pct_ctr]
        
        weighted_avg_vol = float(np.sum(weights * volatilities))
        div_benefit_pct = ((weighted_avg_vol - port_sd) / weighted_avg_vol) * 100.0 if weighted_avg_vol > 0 else 0.0
        
        if delta_sharpe > 0.02 and delta_vol_bps <= 20:
            verdict = f"HIGHLY ACCRETIVE: Adding {candidate_instrument.name} expands the Efficient Frontier (+{delta_sharpe:+.2f} Sharpe) with strong diversification."
        elif delta_ret_bps > 0:
            verdict = f"RETURN ENHANCING: Increases expected return by +{delta_ret_bps:.0f} bps, with moderate risk trade-off."
        else:
            verdict = f"DILUTIVE: Adding this instrument decreases portfolio Sharpe ratio. Consider lower allocation or alternative asset class."

        names_after = [inst.name for inst, _ in port_after.holdings]
        
        sim_res = AdditionSimulationResult(
            candidate_instrument_name=candidate_instrument.name,
            added_dollar_amount=dollar_to_add,
            added_weight_pct=round(added_weight, 2),
            correlation_with_portfolio=assumed_correlation_with_portfolio,
            metrics_before=m_before,
            metrics_after=m_after,
            delta_metrics=deltas,
            mctr_contributions_pct=pct_ctr_normalized,
            holdings_names_after=names_after,
            diversification_benefit_pct=round(div_benefit_pct, 1),
            recommendation_verdict=verdict
        )
        
        fig_3d = self.viz.plot_3d_risk_return_landscape(
            base_return=m_before["expected_annual_return_pct"] / 100.0,
            base_vol=m_before["annual_volatility_pct"] / 100.0,
            candidate_name=candidate_instrument.name,
            candidate_return=candidate_instrument.compute_expected_return(),
            candidate_vol=candidate_instrument.compute_volatility(),
            rf=base_portfolio.rf
        )
        
        fig_bar = self.viz.plot_before_after_migration(m_before, m_after, candidate_instrument.name, added_weight)
        fig_donut = self.viz.plot_marginal_risk_contributions(names_after, pct_ctr_normalized)

        return sim_res, fig_3d, fig_bar, fig_donut

if __name__ == "__main__":
    try:
        from .instruments.fixed_income import FixedCouponBond
        from .instruments.equity import PublicEquityStock, RealEstateAsset
    except ImportError:
        try:
            from cfa_quant.instruments.fixed_income import FixedCouponBond
            from cfa_quant.instruments.equity import PublicEquityStock, RealEstateAsset
        except ImportError:
            from instruments.fixed_income import FixedCouponBond
            from instruments.equity import PublicEquityStock, RealEstateAsset

    print("=" * 75)
    print("🏛️ CFA MARGINAL ALLOCATION & ASSET ADDITION ENGINE")
    print("=" * 75)
    
    base = UnifiedPortfolio("Marcus Family Wealth (Base)")
    base.add_instrument(PublicEquityStock("US Large Cap Equities", beta=1.0, expected_earnings_growth=0.065, historical_volatility=0.18), 6000000.0)
    base.add_instrument(FixedCouponBond("Core US Aggregate Bonds", coupon_rate=0.035, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
    
    re_candidate = RealEstateAsset("Institutional Direct Real Estate Fund", net_operating_income=110000.0, cap_rate=0.055, expected_appreciation_rate=0.035)
    
    engine = MarginalAllocationEngine()
    result, f3d, fbar, fdonut = engine.simulate_asset_addition(base, re_candidate, dollar_to_add=2000000.0)
    
    print(f"Candidate Added: {result.candidate_instrument_name} (+${result.added_dollar_amount:,.2f} / {result.added_weight_pct}%)")
    print(f"Return: {result.metrics_before['expected_annual_return_pct']}% ➔ {result.metrics_after['expected_annual_return_pct']}% (Delta: {result.delta_metrics['return_delta_bps']:+0.1f} bps)")
    print(f"Volatility: {result.metrics_before['annual_volatility_pct']}% ➔ {result.metrics_after['annual_volatility_pct']}% (Delta: {result.delta_metrics['volatility_delta_bps']:+0.1f} bps)")
    print(f"Sharpe Ratio: {result.metrics_before['sharpe_ratio']:.2f} ➔ {result.metrics_after['sharpe_ratio']:.2f} (Delta: {result.delta_metrics['sharpe_delta']:+.2f})")
    print(f"Diversification Benefit: {result.diversification_benefit_pct}%")
    print(f"Verdict: {result.recommendation_verdict}")
    print("=" * 75)
