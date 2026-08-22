"""
Fixed Income Instruments Module (Powered by numpy-financial & CFA Math)
Implements:
1. FixedCouponBond
2. ZeroCouponBond
3. InflationLinkedBond (TIPS)
4. FloatingRateNote (FRN)
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np
import numpy_financial as npf

try:
    from .base import InvestmentInstrument, AssetClass
except ImportError:
    try:
        from cfa_quant.instruments.base import InvestmentInstrument, AssetClass
    except ImportError:
        from base import InvestmentInstrument, AssetClass

@dataclass
class FixedCouponBond(InvestmentInstrument):
    coupon_rate: float = 0.045        # Annual coupon rate (e.g. 0.045)
    maturity_years: float = 10.0      # Years to maturity
    yield_to_maturity: float = 0.045  # Annual YTM
    par_value: float = 1000.0
    payment_frequency: int = 2        # Semiannual (2) or Annual (1)
    credit_rating: str = "AAA"
    
    def __post_init__(self):
        self.asset_class = AssetClass.FIXED_INCOME
        if self.current_market_price == 0.0 or self.current_market_price == 1.0:
            self.current_market_price = self.compute_bond_price()

    def compute_bond_price(self) -> float:
        n_per = int(self.maturity_years * self.payment_frequency)
        rate_per = self.yield_to_maturity / self.payment_frequency
        pmt_per = (self.coupon_rate * self.par_value) / self.payment_frequency
        
        pv = -npf.pv(rate=rate_per, nper=n_per, pmt=pmt_per, fv=self.par_value)
        return round(float(pv), 2)

    def compute_expected_return(self) -> float:
        return self.yield_to_maturity

    def compute_volatility(self) -> float:
        return self.compute_modified_duration() * 0.015

    def compute_duration(self) -> float:
        return self.compute_macaulay_duration()

    def compute_macaulay_duration(self) -> float:
        freq = self.payment_frequency
        periods = int(self.maturity_years * freq)
        pmt = (self.coupon_rate * self.par_value) / freq
        y_per = self.yield_to_maturity / freq
        
        times = np.arange(1, periods + 1) / freq
        cash_flows = np.full(periods, pmt)
        cash_flows[-1] += self.par_value
        
        pv_factors = 1.0 / ((1.0 + y_per) ** np.arange(1, periods + 1))
        pv_cfs = cash_flows * pv_factors
        total_pv = np.sum(pv_cfs)
        
        weights = pv_cfs / total_pv
        mac_dur = np.sum(times * weights)
        return round(float(mac_dur), 3)

    def compute_modified_duration(self) -> float:
        mac_dur = self.compute_macaulay_duration()
        y_per = self.yield_to_maturity / self.payment_frequency
        mod_dur = mac_dur / (1.0 + y_per)
        return round(float(mod_dur), 3)

    def compute_convexity(self) -> float:
        freq = self.payment_frequency
        periods = int(self.maturity_years * freq)
        pmt = (self.coupon_rate * self.par_value) / freq
        y_per = self.yield_to_maturity / freq
        
        t_t_plus_1 = np.arange(1, periods + 1) * (np.arange(1, periods + 1) + 1)
        pv_factors = 1.0 / ((1.0 + y_per) ** np.arange(1, periods + 1))
        cash_flows = np.full(periods, pmt)
        cash_flows[-1] += self.par_value
        
        pv_cfs = cash_flows * pv_factors
        total_pv = np.sum(pv_cfs)
        
        conv = np.sum(t_t_plus_1 * pv_cfs) / (total_pv * ((1.0 + y_per) ** 2) * (freq ** 2))
        return round(float(conv), 3)

@dataclass
class ZeroCouponBond(InvestmentInstrument):
    maturity_years: float = 5.0
    yield_to_maturity: float = 0.045
    par_value: float = 1000.0
    
    def __post_init__(self):
        self.asset_class = AssetClass.FIXED_INCOME
        self.current_market_price = float(-npf.pv(rate=self.yield_to_maturity, nper=self.maturity_years, pmt=0, fv=self.par_value))

    def compute_expected_return(self) -> float:
        return self.yield_to_maturity

    def compute_volatility(self) -> float:
        return self.maturity_years * 0.015

    def compute_duration(self) -> float:
        return float(self.maturity_years)

    def compute_convexity(self) -> float:
        return round((self.maturity_years * (self.maturity_years + 1.0)) / ((1.0 + self.yield_to_maturity) ** 2), 3)

@dataclass
class InflationLinkedBond(FixedCouponBond):
    expected_inflation_rate: float = 0.025
    
    def compute_expected_return(self) -> float:
        return (1.0 + self.yield_to_maturity) * (1.0 + self.expected_inflation_rate) - 1.0
