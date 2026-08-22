"""
Base Investment Instrument Abstract Architecture
Defines standard object-oriented contracts for all financial assets and liabilities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import numpy as np

class AssetClass(Enum):
    GLOBAL_EQUITIES = "Global Equities"
    FIXED_INCOME = "Fixed Income"
    CASH_EQUIVALENTS = "Cash & Equivalents"
    REAL_ESTATE = "Real Estate"
    COMMODITIES = "Commodities"
    PRIVATE_EQUITY = "Private Equity"
    DERIVATIVES = "Derivatives"
    LIABILITY = "Liability Obligation"

@dataclass
class InvestmentInstrument(ABC):
    name: str = "Investment Asset"
    asset_class: AssetClass = AssetClass.GLOBAL_EQUITIES
    current_market_price: float = 0.0
    quantity: float = 1.0
    currency: str = "USD"
    
    @property
    def total_market_value(self) -> float:
        return round(self.current_market_price * self.quantity, 2)

    @abstractmethod
    def compute_expected_return(self) -> float:
        """Returns annualized expected nominal return (e.g. 0.075 for 7.5%)"""
        pass

    @abstractmethod
    def compute_volatility(self) -> float:
        """Returns annualized standard deviation (e.g. 0.18 for 18%)"""
        pass

    def compute_duration(self) -> float:
        """Default Macaulay Duration in years (0 for perpetual/non-fixed-income assets)"""
        return 0.0

    def compute_convexity(self) -> float:
        """Default Convexity measure"""
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "asset_class": self.asset_class.value,
            "current_market_price": self.current_market_price,
            "quantity": self.quantity,
            "total_market_value": self.total_market_value,
            "expected_return_pct": round(self.compute_expected_return() * 100, 2),
            "volatility_pct": round(self.compute_volatility() * 100, 2),
            "duration_years": round(self.compute_duration(), 2),
            "convexity": round(self.compute_convexity(), 2)
        }
