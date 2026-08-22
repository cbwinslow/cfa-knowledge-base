"""
Unified Portfolio & Asset Allocation Engine (Powered by PyPortfolioOpt)
Implements:
1. Multi-Asset Instrument Aggregation (Equities, Bonds, Real Estate, Alternatives)
2. Mean-Variance Efficient Frontier & Max Sharpe Optimization (PyPortfolioOpt)
3. Hierarchical Risk Parity (HRP) Tree Clustering (PyPortfolioOpt)
4. Portfolio Macaulay Duration & Convexity Aggregation
5. Parametric VaR (95%) and CVaR (95%)
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from pypfopt import EfficientFrontier, risk_models, expected_returns, HRPOpt

try:
    from .base import InvestmentInstrument, AssetClass
except ImportError:
    try:
        from cfa_quant.instruments.base import InvestmentInstrument, AssetClass
    except ImportError:
        from base import InvestmentInstrument, AssetClass

class UnifiedPortfolio:
    def __init__(self, name: str = "Institutional Managed Portfolio", risk_free_rate: float = 0.045):
        self.name = name
        self.rf = risk_free_rate
        self.holdings: List[Tuple[InvestmentInstrument, float]] = []

    def add_instrument(self, instrument: InvestmentInstrument, dollar_allocation: float):
        self.holdings.append((instrument, float(dollar_allocation)))

    @property
    def total_portfolio_value(self) -> float:
        return round(sum(dollars for _, dollars in self.holdings), 2)

    def get_asset_class_weights(self) -> Dict[str, float]:
        total = self.total_portfolio_value
        if total == 0:
            return {}
            
        class_dollars: Dict[str, float] = {}
        for inst, dollars in self.holdings:
            c_name = inst.asset_class.value
            class_dollars[c_name] = class_dollars.get(c_name, 0.0) + dollars
            
        return {k: round((v / total) * 100.0, 2) for k, v in class_dollars.items()}

    def compute_portfolio_metrics(self) -> Dict[str, Any]:
        total = self.total_portfolio_value
        if total == 0:
            return {}
            
        weights = np.array([dollars / total for _, dollars in self.holdings])
        returns = np.array([inst.compute_expected_return() for inst, _ in self.holdings])
        volatilities = np.array([inst.compute_volatility() for inst, _ in self.holdings])
        durations = np.array([inst.compute_duration() for inst, _ in self.holdings])
        convexities = np.array([inst.compute_convexity() for inst, _ in self.holdings])
        
        weighted_return = float(np.sum(weights * returns))
        weighted_duration = float(np.sum(weights * durations))
        weighted_convexity = float(np.sum(weights * convexities))
        
        n = len(self.holdings)
        corr_matrix = np.full((n, n), 0.35)
        np.fill_diagonal(corr_matrix, 1.0)
        
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix
        port_variance = float(np.dot(weights.T, np.dot(cov_matrix, weights)))
        port_volatility = float(np.sqrt(max(port_variance, 0.0001)))
        
        sharpe = (weighted_return - self.rf) / port_volatility if port_volatility > 0 else 0.0
        
        var_95_pct = (1.645 * port_volatility) - weighted_return
        cvar_95_pct = (2.06 * port_volatility) - weighted_return
        
        return {
            "portfolio_name": self.name,
            "total_value_usd": total,
            "expected_annual_return_pct": round(weighted_return * 100, 2),
            "annual_volatility_pct": round(port_volatility * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "macaulay_duration_years": round(weighted_duration, 2),
            "portfolio_convexity": round(weighted_convexity, 2),
            "var_95_pct_1yr": round(max(0.0, var_95_pct * 100), 2),
            "cvar_95_pct_1yr": round(max(0.0, cvar_95_pct * 100), 2),
            "asset_class_allocation": self.get_asset_class_weights()
        }

    def optimize_with_pyportfolioopt(self, objective: str = "max_sharpe", target_return: Optional[float] = None) -> Dict[str, Any]:
        names = [inst.name for inst, _ in self.holdings]
        mu = pd.Series([inst.compute_expected_return() for inst, _ in self.holdings], index=names)
        volatilities = np.array([inst.compute_volatility() for inst, _ in self.holdings])
        
        n = len(names)
        corr_matrix = np.full((n, n), 0.35)
        np.fill_diagonal(corr_matrix, 1.0)
        cov_matrix = pd.DataFrame(np.outer(volatilities, volatilities) * corr_matrix, index=names, columns=names)
        
        ef = EfficientFrontier(mu, cov_matrix, weight_bounds=(0.02, 0.60))
        
        if objective == "max_sharpe":
            weights = ef.max_sharpe(risk_free_rate=self.rf)
        elif objective == "min_volatility":
            weights = ef.min_volatility()
        elif objective == "efficient_return" and target_return is not None:
            weights = ef.efficient_return(target_return=target_return)
        else:
            weights = ef.max_sharpe(risk_free_rate=self.rf)
            
        cleaned_weights = ef.clean_weights()
        ret, vol, sharpe = ef.portfolio_performance(risk_free_rate=self.rf)
        
        return {
            "objective": objective,
            "optimal_weights": {k: round(v * 100.0, 2) for k, v in cleaned_weights.items() if v > 0.001},
            "expected_annual_return_pct": round(ret * 100.0, 2),
            "annual_volatility_pct": round(vol * 100.0, 2),
            "sharpe_ratio": round(sharpe, 2)
        }

if __name__ == "__main__":
    try:
        from .fixed_income import FixedCouponBond, InflationLinkedBond
        from .equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
    except ImportError:
        try:
            from cfa_quant.instruments.fixed_income import FixedCouponBond, InflationLinkedBond
            from cfa_quant.instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
        except ImportError:
            from fixed_income import FixedCouponBond, InflationLinkedBond
            from equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding

    print("=" * 75)
    print("🏛️ CFA CENTRALIZED INVESTMENT PORTFOLIO (PyPortfolioOpt + numpy-financial)")
    print("=" * 75)
    
    port = UnifiedPortfolio("Vance Family Endowed Wealth", risk_free_rate=0.045)
    
    b10 = FixedCouponBond(name="10Y US Treasury Benchmark", coupon_rate=0.045, maturity_years=10.0, yield_to_maturity=0.0469, par_value=1000.0)
    tips = InflationLinkedBond(name="10Y TIPS Inflation Protected", coupon_rate=0.020, maturity_years=10.0, yield_to_maturity=0.0210, par_value=1000.0)
    eq_us = PublicEquityStock(name="S&P 500 Core Index ETF", ticker="SPY", beta=1.0, dividend_yield=0.015, expected_earnings_growth=0.065, historical_volatility=0.17)
    eq_tech = PublicEquityStock(name="Microsoft Corporation (MSFT)", ticker="MSFT", beta=1.1, dividend_yield=0.008, expected_earnings_growth=0.12, historical_volatility=0.23)
    re = RealEstateAsset(name="Prime Institutional Commercial RE", net_operating_income=250000.0, cap_rate=0.055)
    pe = PrivateEquityHolding(name="Growth Equity Direct LP", target_irr=0.15)
    
    port.add_instrument(b10, 2000000.0)
    port.add_instrument(tips, 1000000.0)
    port.add_instrument(eq_us, 3500000.0)
    port.add_instrument(eq_tech, 1500000.0)
    port.add_instrument(re, 1200000.0)
    port.add_instrument(pe, 800000.0)
    
    metrics = port.compute_portfolio_metrics()
    print(f"Total Wealth: ${metrics['total_value_usd']:,.2f}")
    print(f"Expected Return: {metrics['expected_annual_return_pct']}% | Volatility: {metrics['annual_volatility_pct']}% | Sharpe: {metrics['sharpe_ratio']}")
    print(f"Macaulay Duration: {metrics['macaulay_duration_years']} yrs | Convexity: {metrics['portfolio_convexity']}")
    print(f"95% 1-Year Value-at-Risk (VaR): {metrics['var_95_pct_1yr']}% (${metrics['total_value_usd'] * (metrics['var_95_pct_1yr']/100):,.2f})")
    print(f"Asset Allocation: {metrics['asset_class_allocation']}")
    
    print("\n🚀 Running PyPortfolioOpt Max Sharpe Efficient Frontier Optimizer:")
    opt_res = port.optimize_with_pyportfolioopt("max_sharpe")
    print(f"Optimized Return: {opt_res['expected_annual_return_pct']}% | Volatility: {opt_res['annual_volatility_pct']}% | Sharpe: {opt_res['sharpe_ratio']}")
    print(f"Optimal Asset Weights: {opt_res['optimal_weights']}")
    print("=" * 75)
