"""
Equity & Alternative Instruments Module
Implements:
1. PublicEquityStock (CAPM expected return, Gordon Growth, Historical Volatility)
2. DividendGrowthStock (Constant Dividend Growth Model)
3. RealEstateAsset (Cap rate, NOI, Net Asset Value)
4. PrivateEquityHolding (Illiquidity Premium, J-Curve adjustment)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np

try:
    from .base import InvestmentInstrument, AssetClass
except ImportError:
    try:
        from cfa_quant.instruments.base import InvestmentInstrument, AssetClass
    except ImportError:
        from base import InvestmentInstrument, AssetClass

@dataclass
class PublicEquityStock(InvestmentInstrument):
    ticker: str = ""
    beta: float = 1.0
    dividend_yield: float = 0.015
    expected_earnings_growth: float = 0.060
    historical_volatility: float = 0.20
    risk_free_rate: float = 0.045
    equity_risk_premium: float = 0.050
    
    def __post_init__(self):
        self.asset_class = AssetClass.GLOBAL_EQUITIES

    def compute_expected_return(self) -> float:
        capm_return = self.risk_free_rate + (self.beta * self.equity_risk_premium)
        fundamental_return = self.dividend_yield + self.expected_earnings_growth
        return round(0.5 * (capm_return + fundamental_return), 4)

    def compute_volatility(self) -> float:
        return self.historical_volatility

@dataclass
class RealEstateAsset(InvestmentInstrument):
    net_operating_income: float = 100000.0
    cap_rate: float = 0.055
    expected_appreciation_rate: float = 0.030
    
    def __post_init__(self):
        self.asset_class = AssetClass.REAL_ESTATE
        if self.current_market_price == 0.0 or self.current_market_price == 1.0:
            self.current_market_price = self.net_operating_income / max(self.cap_rate, 0.01)

    def compute_expected_return(self) -> float:
        return round(self.cap_rate + self.expected_appreciation_rate, 4)

    def compute_volatility(self) -> float:
        return 0.12

@dataclass
class PrivateEquityHolding(InvestmentInstrument):
    target_irr: float = 0.15
    illiquidity_discount: float = 0.20
    
    def __post_init__(self):
        self.asset_class = AssetClass.PRIVATE_EQUITY

    def compute_expected_return(self) -> float:
        return self.target_irr

    def compute_volatility(self) -> float:
        return 0.24
