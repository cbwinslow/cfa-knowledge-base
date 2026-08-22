"""
Opportunity Cost & Capital Allocation Assessment Engine
Evaluates:
1. Yield Spreads vs 10-Yr Treasury & Cash Equivalents
2. Economic Value Added (EVA) Spread: ROIC vs WACC Hurdle Rate
3. Next-Best Competitor Alternative Analysis (Pairwise Opportunity Cost)
"""

from typing import Dict, Any, List
from .models import OpportunityCostAssessment

class OpportunityCostEngine:
    def __init__(self, risk_free_rate: float = 0.0474, equity_risk_premium: float = 0.050):
        self.rf = risk_free_rate
        self.erp = equity_risk_premium
        self.market_expected_return = self.rf + self.erp

    def evaluate_opportunity_cost(
        self,
        ticker: str,
        current_price: float,
        market_cap: float,
        latest_cfo: float,
        latest_capex: float,
        ebit: float,
        total_debt: float,
        stockholders_equity: float,
        cash: float,
        wacc: float,
        peer_metrics: List[Dict[str, Any]]
    ) -> OpportunityCostAssessment:
        """
        Evaluates whether allocating capital to this security beats both the macro hurdle rate
        and the industry's next-best alternative.
        """
        # 1. Free Cash Flow Yield
        fcf = max(0.0, latest_cfo - latest_capex)
        fcf_yield = (fcf / max(market_cap, 1.0)) * 100.0
        
        # 2. Spread over 10-Yr Treasury (Opportunity cost of holding equities vs risk-free government debt)
        rf_pct = self.rf * 100.0
        fcf_spread_treasury_bps = (fcf_yield - rf_pct) * 100.0
        
        # 3. ROIC vs WACC Spread (Economic Value Added)
        nopat = ebit * (1.0 - 0.21)
        invested_capital = max(total_debt + stockholders_equity - cash, 1.0)
        roic_pct = (nopat / invested_capital) * 100.0
        wacc_pct = wacc * 100.0
        eva_spread = roic_pct - wacc_pct
        
        hurdle_cleared = (roic_pct > wacc_pct) and (fcf_yield >= (self.rf * 100.0 * 0.75))
        
        # 4. Next-Best Competitor Opportunity Cost
        # Find the competitor with the highest EVA spread
        best_peer = None
        best_peer_eva = -999.0
        
        for p in peer_metrics:
            if p["ticker"] != ticker.upper():
                peer_eva = p.get("roic", 0.0) - (wacc_pct * 0.95)  # approximate peer WACC
                if peer_eva > best_peer_eva:
                    best_peer_eva = peer_eva
                    best_peer = p["ticker"]
                    
        next_best_ticker = best_peer or "N/A"
        
        # Formulate Verdict
        if eva_spread > 10.0 and fcf_spread_treasury_bps > 0:
            verdict = "SUPERIOR CAPITAL ALLOCATION: Generates massive economic profit above WACC and beats Treasury yield."
        elif eva_spread > 0 and eva_spread >= best_peer_eva:
            verdict = "COMPETITIVELY ADVANTAGED: Clears hurdle rate and represents the premier industry capital return choice."
        elif best_peer and best_peer_eva > (eva_spread + 5.0):
            verdict = f"OPPORTUNITY COST WARNING: Peer {next_best_ticker} offers higher capital efficiency (EVA Spread: {best_peer_eva:+.1f}% vs {eva_spread:+.1f}%)."
        elif eva_spread <= 0:
            verdict = "ECONOMIC VALUE DESTRUCTION: ROIC fails to cover cost of capital (WACC). Capital is better deployed in Treasury/Cash."
        else:
            verdict = "MODERATE RETURN: Meets cost of capital, but provides modest equity risk premium."
            
        return OpportunityCostAssessment(
            ticker=ticker.upper(),
            market_price=round(current_price, 2),
            fcf_yield_pct=round(fcf_yield, 2),
            risk_free_rate_pct=round(rf_pct, 2),
            equity_risk_premium_pct=round(self.erp * 100, 2),
            fcf_yield_spread_over_treasury_bps=round(fcf_spread_treasury_bps, 1),
            roic_pct=round(roic_pct, 2),
            wacc_pct=round(wacc_pct, 2),
            economic_value_added_spread_pct=round(eva_spread, 2),
            hurdle_rate_cleared=hurdle_cleared,
            next_best_competitor_ticker=next_best_ticker,
            next_best_competitor_eva_spread=round(best_peer_eva, 2),
            opportunity_cost_verdict=verdict
        )
