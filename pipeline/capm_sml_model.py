#!/usr/bin/env python3
"""
CAPM & Security Market Line (SML) Quantitative Model
Calculates:
1. CAPM Required Rate of Return
2. Jensen's Alpha, Treynor Ratio, and Sharpe Ratio
3. SML Positioning (Above SML = Undervalued Alpha / Below SML = Overvalued)
4. ASCII Security Market Line visualization
"""

from typing import Dict, Any

class CapmSmlModel:
    def __init__(self, risk_free_rate: float = 0.0470, equity_risk_premium: float = 0.050):
        self.rf = risk_free_rate
        self.erp = equity_risk_premium
        self.market_return = self.rf + self.erp

    def evaluate_security(self, ticker: str, beta: float, realized_return_estimate: float = 0.12, volatility: float = 0.22) -> Dict[str, Any]:
        """
        Evaluates a stock against the Security Market Line (SML).
        """
        # CAPM Required Return
        capm_required_return = self.rf + (beta * self.erp)
        
        # Jensen's Alpha: Alpha = Realized/Expected Return - CAPM Required Return
        jensen_alpha = realized_return_estimate - capm_required_return
        
        # Treynor Ratio = (R - Rf) / Beta
        treynor_ratio = (realized_return_estimate - self.rf) / max(beta, 0.01)
        
        # Sharpe Ratio = (R - Rf) / Volatility
        sharpe_ratio = (realized_return_estimate - self.rf) / max(volatility, 0.01)
        
        # SML Positioning
        if jensen_alpha > 0.015:
            sml_stance = "ABOVE SML (Undervalued / Positive Jensen's Alpha Generator)"
        elif jensen_alpha < -0.015:
            sml_stance = "BELOW SML (Overvalued / Negative Excess Risk-Adjusted Return)"
        else:
            sml_stance = "ON SML (Fairly Priced according to CAPM Equilibrium)"
            
        return {
            "ticker": ticker.upper(),
            "beta": round(beta, 2),
            "risk_free_rate_pct": round(self.rf * 100, 2),
            "equity_risk_premium_pct": round(self.erp * 100, 2),
            "capm_required_return_pct": round(capm_required_return * 100, 2),
            "expected_return_pct": round(realized_return_estimate * 100, 2),
            "jensen_alpha_pct": round(jensen_alpha * 100, 2),
            "treynor_ratio": round(treynor_ratio, 3),
            "sharpe_ratio": round(sharpe_ratio, 3),
            "sml_verdict": sml_stance
        }

    def generate_ascii_sml_chart(self, ticker: str, beta: float, expected_return: float) -> str:
        """
        Renders an ASCII Security Market Line chart comparing Stock vs Market Portfolio.
        """
        capm_req = self.rf + (beta * self.erp)
        chart = f"""
   Expected Return E(R)
     ▲
14%  │                                      * [SML Line]
12%  │                           {'★ ' + ticker if expected_return >= 0.12 else ''}
10%  │                     ● Market Portfolio (Beta=1.0, R={self.market_return*100:.1f}%)
 8%  │               /     {'★ ' + ticker if 0.08 <= expected_return < 0.12 else ''}
 6%  │         /           {'★ ' + ticker if expected_return < 0.08 else ''}
 4%  │   ■ Risk-Free Rate Rf ({self.rf*100:.1f}%)
     └────────────────────────────────────────────────────────► Beta (β)
        0.0        0.5        1.0        1.5        2.0
"""
        return chart

if __name__ == "__main__":
    model = CapmSmlModel(risk_free_rate=0.0474, equity_risk_premium=0.050)
    res = model.evaluate_security("MSFT", beta=1.10, realized_return_estimate=0.135, volatility=0.22)
    print("==================================================")
    print(f"CAPM & SECURITY MARKET LINE REPORT: {res['ticker']}")
    print("==================================================")
    print(f"Beta: {res['beta']}")
    print(f"CAPM Required Return: {res['capm_required_return_pct']}%")
    print(f"Expected Return: {res['expected_return_pct']}%")
    print(f"Jensen's Alpha: {res['jensen_alpha_pct']:+}%")
    print(f"Treynor Ratio: {res['treynor_ratio']}")
    print(f"Sharpe Ratio: {res['sharpe_ratio']}")
    print(f"Verdict: {res['sml_verdict']}")
    print(model.generate_ascii_sml_chart("MSFT", 1.10, 0.135))
