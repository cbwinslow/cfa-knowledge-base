"""
Capital Market Expectations (CME) Engine - CFA Level III Standards
Implements:
1. Grinold-Kroner Model (Expected Equity Return)
2. Singer-Terhaar Model (Multi-Asset Global Integrated/Segmented Expected Return)
3. Fixed Income Yield Decomposition (Building Block Approach)
"""

from typing import Dict, Any, List
import numpy as np

class CapitalMarketExpectationsEngine:
    def __init__(self):
        pass

    def compute_grinold_kroner_expected_return(
        self,
        dividend_yield: float = 0.018,
        expected_inflation: float = 0.025,
        real_earnings_growth: float = 0.020,
        expected_share_repurchase_yield: float = 0.010,  # Negative if diluting shares
        repricing_multiple_change_annualized: float = 0.000
    ) -> Dict[str, Any]:
        """
        CFA Level III Grinold-Kroner Model:
        E(R) = Income Return + Nominal Earnings Growth + Repricing
        Income Return = D/P - Delta S (Dividend Yield + Net Buyback Yield)
        Nominal Earnings Growth = Expected Inflation (i) + Real GDP/Earnings Growth (g)
        Repricing = Delta(P/E)
        """
        income_return = dividend_yield + expected_share_repurchase_yield
        nominal_earnings_growth = expected_inflation + real_earnings_growth
        repricing = repricing_multiple_change_annualized
        
        expected_nominal_equity_return = income_return + nominal_earnings_growth + repricing
        
        return {
            "dividend_yield_pct": round(dividend_yield * 100, 2),
            "share_repurchase_yield_pct": round(expected_share_repurchase_yield * 100, 2),
            "total_cash_flow_yield_pct": round(income_return * 100, 2),
            "expected_inflation_pct": round(expected_inflation * 100, 2),
            "real_earnings_growth_pct": round(real_earnings_growth * 100, 2),
            "repricing_multiple_change_pct": round(repricing * 100, 2),
            "expected_nominal_equity_return_pct": round(expected_nominal_equity_return * 100, 2)
        }

    def compute_singer_terhaar_expected_return(
        self,
        asset_name: str,
        asset_volatility: float,
        global_market_sharpe: float = 0.35,
        correlation_with_global_market: float = 0.75,
        degree_of_market_integration: float = 0.80,  # phi between 0 (fully segmented) and 1 (fully integrated)
        risk_free_rate: float = 0.045,
        illiquidity_premium: float = 0.000
    ) -> Dict[str, Any]:
        """
        CFA Level III Singer-Terhaar Model:
        Expected Risk Premium under Full Integration: ERP_i^G = beta_i,G * (Sharpe_G * sigma_G) = corr_i,G * sigma_i * Sharpe_G
        Expected Risk Premium under Full Segmentation: ERP_i^S = sigma_i * Sharpe_G
        Blended Expected Risk Premium: ERP_i = phi * ERP_i^G + (1 - phi) * ERP_i^S
        Total Expected Return: E(R_i) = R_f + ERP_i + Illiquidity Premium
        """
        # Risk premium assuming fully integrated global market
        erp_integrated = correlation_with_global_market * asset_volatility * global_market_sharpe
        
        # Risk premium assuming fully segmented local market
        erp_segmented = asset_volatility * global_market_sharpe
        
        # Blended risk premium based on integration degree (phi)
        blended_erp = (degree_of_market_integration * erp_integrated) + ((1.0 - degree_of_market_integration) * erp_segmented)
        
        total_expected_return = risk_free_rate + blended_erp + illiquidity_premium
        
        return {
            "asset_name": asset_name,
            "risk_free_rate_pct": round(risk_free_rate * 100, 2),
            "integrated_risk_premium_pct": round(erp_integrated * 100, 2),
            "segmented_risk_premium_pct": round(erp_segmented * 100, 2),
            "blended_equity_risk_premium_pct": round(blended_erp * 100, 2),
            "illiquidity_premium_pct": round(illiquidity_premium * 100, 2),
            "total_expected_return_pct": round(total_expected_return * 100, 2)
        }

    def compute_fixed_income_building_blocks(
        self,
        real_risk_free_rate: float = 0.020,
        expected_inflation: float = 0.025,
        term_premium: float = 0.005,
        credit_spread: float = 0.015,
        expected_credit_loss: float = 0.003
    ) -> Dict[str, Any]:
        """
        CFA Level III Fixed Income Building Block Model:
        E(R_bond) = Real Rf + Inflation + Term Premium + Credit Spread - Expected Default Loss
        """
        nominal_rf = real_risk_free_rate + expected_inflation
        expected_bond_return = nominal_rf + term_premium + (credit_spread - expected_credit_loss)
        
        return {
            "nominal_risk_free_rate_pct": round(nominal_rf * 100, 2),
            "term_premium_pct": round(term_premium * 100, 2),
            "net_credit_premium_pct": round((credit_spread - expected_credit_loss) * 100, 2),
            "expected_total_bond_return_pct": round(expected_bond_return * 100, 2)
        }

if __name__ == "__main__":
    cme = CapitalMarketExpectationsEngine()
    print("=" * 70)
    print("🏛️ CFA LEVEL III CAPITAL MARKET EXPECTATIONS (CME) ENGINE")
    print("=" * 70)
    
    gk = cme.compute_grinold_kroner_expected_return(dividend_yield=0.016, expected_inflation=0.025, real_earnings_growth=0.022, expected_share_repurchase_yield=0.012)
    print(f"Grinold-Kroner S&P 500 Expected Nominal Return: {gk['expected_nominal_equity_return_pct']}%")
    print(f"  • Income Component (Div + Buyback): {gk['total_cash_flow_yield_pct']}%")
    print(f"  • Nominal Earnings Growth: {gk['expected_inflation_pct'] + gk['real_earnings_growth_pct']:.2f}%")
    
    st_res = cme.compute_singer_terhaar_expected_return("Emerging Markets Equities", asset_volatility=0.24, correlation_with_global_market=0.65, degree_of_market_integration=0.70, risk_free_rate=0.045, illiquidity_premium=0.010)
    print(f"\nSinger-Terhaar Emerging Markets Expected Return: {st_res['total_expected_return_pct']}%")
    print(f"  • Blended ERP: {st_res['blended_equity_risk_premium_pct']}% (Integration: 70%)")
    print("=" * 70)
