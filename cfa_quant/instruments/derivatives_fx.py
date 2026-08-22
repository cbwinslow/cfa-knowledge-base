"""
Comprehensive Derivatives & Foreign Exchange (FX) Instruments Module
Implements:
1. InterestRateSwap (Fixed-for-Floating Par Swap Rate, MTM Valuation, Swap Duration)
2. ForexForward & Cross-Currency Swap (Covered Interest Rate Parity, Forward Points, MTM)
3. EquityIndexFutures & CommodityFutures (Cost of Carry, Storage Costs, Target Duration/Beta Hedging)
4. OptionsContract (Black-Scholes-Merton with Greeks & Common Spread Payoffs)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from scipy.stats import norm

try:
    from .base import InvestmentInstrument, AssetClass
except ImportError:
    try:
        from cfa_quant.instruments.base import InvestmentInstrument, AssetClass
    except ImportError:
        from base import InvestmentInstrument, AssetClass

@dataclass
class InterestRateSwap(InvestmentInstrument):
    """
    CFA Level II/III Fixed-for-Floating Interest Rate Swap (SOFR Reference)
    """
    notional_principal: float = 10000000.0  # $10M Notional
    fixed_swap_rate: float = 0.0425         # Fixed rate paid or received (e.g. 4.25%)
    floating_rate_current: float = 0.0450   # Current floating rate (e.g. SOFR)
    maturity_years: float = 5.0             # Tenor in years
    payment_frequency: int = 2              # Semiannual (2) or Annual (1)
    is_payer: bool = True                   # True if paying Fixed / receiving Floating
    discount_curve_rates: List[float] = field(default_factory=lambda: [0.040, 0.042, 0.044, 0.046, 0.048])
    
    def __post_init__(self):
        self.asset_class = AssetClass.DERIVATIVES
        self.quantity = self.notional_principal
        self.current_market_price = self.compute_mark_to_market_value() / self.notional_principal

    def compute_par_swap_rate(self) -> float:
        """
        Calculates the equilibrium par swap rate (where initial value is 0):
        R_swap = (1 - Z_N) / sum(Z_i)
        """
        freq = self.payment_frequency
        periods = int(self.maturity_years * freq)
        times = np.arange(1, periods + 1) / freq
        
        # Linear interpolation across discount curve
        curve = self.discount_curve_rates
        rates = np.interp(times, np.linspace(1, self.maturity_years, len(curve)), curve)
        discount_factors = 1.0 / ((1.0 + (rates / freq)) ** np.arange(1, periods + 1))
        
        z_n = discount_factors[-1]
        sum_z = np.sum(discount_factors)
        par_rate_per_period = (1.0 - z_n) / sum_z
        annual_par_swap_rate = par_rate_per_period * freq
        return round(float(annual_par_swap_rate), 4)

    def compute_mark_to_market_value(self) -> float:
        """
        Calculates MTM value of the swap:
        V_payer = Notional * (R_current_par - R_contract_fixed) * sum(Z_i)
        """
        freq = self.payment_frequency
        periods = int(self.maturity_years * freq)
        times = np.arange(1, periods + 1) / freq
        
        curve = self.discount_curve_rates
        rates = np.interp(times, np.linspace(1, self.maturity_years, len(curve)), curve)
        discount_factors = 1.0 / ((1.0 + (rates / freq)) ** np.arange(1, periods + 1))
        sum_z = np.sum(discount_factors)
        
        current_par = self.compute_par_swap_rate()
        delta_rate = (current_par - self.fixed_swap_rate) / freq
        mtm_val = self.notional_principal * delta_rate * sum_z
        
        return round(float(mtm_val if self.is_payer else -mtm_val), 2)

    def compute_duration(self) -> float:
        """
        CFA Swap Duration:
        Payer Swap: D_payer = D_floating - D_fixed ~= 0.25 - 0.75 * Maturity (Negative Duration)
        Receiver Swap: D_receiver = D_fixed - D_floating (Positive Duration)
        """
        d_floating = 0.5 / self.payment_frequency  # Half of payment period
        d_fixed = 0.75 * self.maturity_years       # Approx fixed bond duration
        swap_dur = (d_floating - d_fixed) if self.is_payer else (d_fixed - d_floating)
        return round(float(swap_dur), 2)

    def compute_expected_return(self) -> float:
        return 0.0  # Swaps are zero-cost derivative overlays

    def compute_volatility(self) -> float:
        return abs(self.compute_duration()) * 0.015

@dataclass
class ForexForward(InvestmentInstrument):
    """
    CFA FX Forward Contract (Covered Interest Rate Parity - CIRP)
    """
    pair: str = "EUR/USD"                   # Price/Base (USD per 1 EUR)
    spot_exchange_rate: float = 1.0850      # Spot rate S_0
    contract_forward_rate: float = 1.0920   # Agreed forward rate F_0
    domestic_risk_free: float = 0.0450      # USD interest rate r_d
    foreign_risk_free: float = 0.0325       # EUR interest rate r_f
    tenor_years: float = 1.0                # Time to maturity
    notional_foreign_currency: float = 5000000.0 # 5M EUR
    is_long_base: bool = True               # True if buying EUR / selling USD
    
    def __post_init__(self):
        self.asset_class = AssetClass.DERIVATIVES
        self.current_market_price = self.spot_exchange_rate

    def compute_theoretical_forward_rate(self) -> float:
        """
        Covered Interest Rate Parity:
        F_CIRP = S_0 * (1 + r_d * T) / (1 + r_f * T)
        """
        f_rate = self.spot_exchange_rate * ((1.0 + self.domestic_risk_free * self.tenor_years) / (1.0 + self.foreign_risk_free * self.tenor_years))
        return round(float(f_rate), 4)

    def compute_forward_points(self) -> float:
        """Forward Points = (F - S) * 10,000 pips"""
        f_theo = self.compute_theoretical_forward_rate()
        points = (f_theo - self.spot_exchange_rate) * 10000.0
        return round(float(points), 1)

    def compute_mark_to_market_value_usd(self) -> float:
        """
        MTM Value at time t:
        V = Notional * [ (F_t - F_0) / (1 + r_d)^T ]
        """
        f_current = self.compute_theoretical_forward_rate()
        delta_f = f_current - self.contract_forward_rate
        pv_factor = 1.0 / (1.0 + self.domestic_risk_free * self.tenor_years)
        val = self.notional_foreign_currency * delta_f * pv_factor
        return round(float(val if self.is_long_base else -val), 2)

    def compute_expected_return(self) -> float:
        return self.domestic_risk_free - self.foreign_risk_free

    def compute_volatility(self) -> float:
        return 0.08  # Typical G10 FX volatility (~8%)

@dataclass
class EquityIndexFutures(InvestmentInstrument):
    """
    CFA Level III Equity Futures & Target Beta Hedging
    """
    underlying_index_spot: float = 5800.0   # S&P 500 spot index
    multiplier: float = 50.0                # E-mini multiplier ($50 per index point)
    time_to_expiration_years: float = 0.25  # 3 months
    risk_free_rate: float = 0.045
    dividend_yield: float = 0.015
    num_contracts: int = 20
    is_long: bool = True
    
    def __post_init__(self):
        self.asset_class = AssetClass.DERIVATIVES
        self.current_market_price = self.compute_futures_price()

    def compute_futures_price(self) -> float:
        """Cost of Carry: F_0 = S_0 * exp((r - q) * T)"""
        f_price = self.underlying_index_spot * np.exp((self.risk_free_rate - self.dividend_yield) * self.time_to_expiration_years)
        return round(float(f_price), 2)

    @property
    def total_notional_value(self) -> float:
        return round(self.compute_futures_price() * self.multiplier * abs(self.num_contracts), 2)

    def calculate_contracts_for_target_beta(self, portfolio_value: float, portfolio_beta: float, target_beta: float) -> int:
        """
        CFA Level III Target Beta Formula:
        N* = [(Beta_target - Beta_portfolio) / Beta_futures] * (Portfolio_Value / Futures_Price * Multiplier)
        """
        futures_notional_per_contract = self.compute_futures_price() * self.multiplier
        beta_gap = target_beta - portfolio_beta
        n_exact = (beta_gap / 1.0) * (portfolio_value / futures_notional_per_contract)
        return int(round(n_exact))

    def compute_expected_return(self) -> float:
        return 0.075

    def compute_volatility(self) -> float:
        return 0.17

@dataclass
class OptionsContract(InvestmentInstrument):
    """
    CFA Black-Scholes-Merton (BSM) Options Instrument with Analytical Greeks
    """
    spot_price: float = 500.0
    strike_price: float = 500.0
    time_to_expiry_years: float = 0.25  # 90 Days
    risk_free_rate: float = 0.045
    implied_volatility: float = 0.22    # 22% Vol
    dividend_yield: float = 0.015
    option_type: str = "call"           # 'call' or 'put'
    num_contracts: int = 10             # 1 contract = 100 shares
    
    def __post_init__(self):
        self.asset_class = AssetClass.DERIVATIVES
        self.current_market_price = self.compute_bsm_price()

    def _compute_d1_d2(self) -> Tuple[float, float]:
        s, k, t, r, q, v = self.spot_price, self.strike_price, self.time_to_expiry_years, self.risk_free_rate, self.dividend_yield, self.implied_volatility
        d1 = (np.log(s / k) + (r - q + 0.5 * (v ** 2)) * t) / (v * np.sqrt(t))
        d2 = d1 - (v * np.sqrt(t))
        return float(d1), float(d2)

    def compute_bsm_price(self) -> float:
        s, k, t, r, q = self.spot_price, self.strike_price, self.time_to_expiry_years, self.risk_free_rate, self.dividend_yield
        d1, d2 = self._compute_d1_d2()
        
        if self.option_type.lower() == "call":
            price = (s * np.exp(-q * t) * norm.cdf(d1)) - (k * np.exp(-r * t) * norm.cdf(d2))
        else:
            price = (k * np.exp(-r * t) * norm.cdf(-d2)) - (s * np.exp(-q * t) * norm.cdf(-d1))
            
        return round(float(price), 2)

    def compute_greeks(self) -> Dict[str, float]:
        s, k, t, r, q, v = self.spot_price, self.strike_price, self.time_to_expiry_years, self.risk_free_rate, self.dividend_yield, self.implied_volatility
        d1, d2 = self._compute_d1_d2()
        
        if self.option_type.lower() == "call":
            delta = np.exp(-q * t) * norm.cdf(d1)
            theta = (- (s * v * np.exp(-q * t) * norm.pdf(d1)) / (2 * np.sqrt(t))) - (r * k * np.exp(-r * t) * norm.cdf(d2)) + (q * s * np.exp(-q * t) * norm.cdf(d1))
            rho = k * t * np.exp(-r * t) * norm.cdf(d2)
        else:
            delta = -np.exp(-q * t) * norm.cdf(-d1)
            theta = (- (s * v * np.exp(-q * t) * norm.pdf(d1)) / (2 * np.sqrt(t))) + (r * k * np.exp(-r * t) * norm.cdf(-d2)) - (q * s * np.exp(-q * t) * norm.cdf(-d1))
            rho = -k * t * np.exp(-r * t) * norm.cdf(-d2)
            
        gamma = (np.exp(-q * t) * norm.pdf(d1)) / (s * v * np.sqrt(t))
        vega = s * np.exp(-q * t) * norm.pdf(d1) * np.sqrt(t)
        
        return {
            "delta": round(float(delta), 4),
            "gamma": round(float(gamma), 4),
            "vega_per_1pct": round(float(vega * 0.01), 4),
            "theta_per_day": round(float(theta / 365.0), 4),
            "rho_per_1pct": round(float(rho * 0.01), 4)
        }

    def compute_expected_return(self) -> float:
        return 0.12 if self.option_type == "call" else -0.05

    def compute_volatility(self) -> float:
        return self.implied_volatility * 2.5
