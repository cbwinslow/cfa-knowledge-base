"""
Centralized CFA Investment Instruments & Portfolio Management Package
Exports:
- Base: InvestmentInstrument, AssetClass
- Fixed Income: FixedCouponBond, ZeroCouponBond, InflationLinkedBond
- Equities & Alternatives: PublicEquityStock, RealEstateAsset, PrivateEquityHolding
- Portfolio: UnifiedPortfolio (PyPortfolioOpt + numpy-financial powered)
"""

from .base import InvestmentInstrument, AssetClass
from .fixed_income import FixedCouponBond, ZeroCouponBond, InflationLinkedBond
from .equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
from .portfolio import UnifiedPortfolio

__all__ = [
    "InvestmentInstrument",
    "AssetClass",
    "FixedCouponBond",
    "ZeroCouponBond",
    "InflationLinkedBond",
    "PublicEquityStock",
    "RealEstateAsset",
    "PrivateEquityHolding",
    "UnifiedPortfolio"
]
