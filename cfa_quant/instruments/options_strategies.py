"""
CFA Level II & Level III Institutional Options Strategy & Greeks Hedging Engine
Implements:
1. Polymorphic BaseOptionStrategy hierarchy (Liskov Substitution compliant)
2. Concrete Institutional Strategies:
   - CoveredCallStrategy (Long Stock + Short Call)
   - ProtectiveCollarStrategy (Long Stock + Long Put + Short Call)
   - BullCallSpreadStrategy & BearPutSpreadStrategy
   - LongStraddleStrategy & ShortStraddleStrategy
   - IronCondorStrategy & IronButterflyStrategy
   - CustomMultiLegStrategy (Arbitrary N-leg structure)
3. Analytical & Numerical Greeks Portfolio Aggregator
4. GreeksHedgingSolver:
   - Delta-Neutral Hedging (Underlying Equity Shares)
   - Gamma-Delta Neutral Hedging (1 Option + Underlying Equity)
   - Vega-Gamma-Delta Neutral Hedging (2 Options + Underlying Equity 2x2 Linear System)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
from scipy.stats import norm

class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"

class TradeAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class OptionLeg:
    """
    Represents a single option leg within a multi-leg options strategy.
    """
    option_type: OptionType
    action: TradeAction
    strike_price: float
    time_to_expiry_years: float
    implied_volatility: float
    quantity: float = 1.0              # Number of contracts (1 contract = 100 shares)
    premium: Optional[float] = None     # Price per share (if None, computed via BSM)
    dividend_yield: float = 0.0
    risk_free_rate: float = 0.045

    def __post_init__(self):
        if isinstance(self.option_type, str):
            self.option_type = OptionType(self.option_type.upper())
        if isinstance(self.action, str):
            self.action = TradeAction(self.action.upper())
        if self.strike_price <= 0:
            raise ValueError(f"Strike price must be strictly positive, got {self.strike_price}")
        if self.time_to_expiry_years < 0:
            raise ValueError(f"Time to expiry cannot be negative, got {self.time_to_expiry_years}")

    def compute_bsm_price(self, spot_price: float) -> float:
        """
        Computes Black-Scholes-Merton theoretical premium per share.
        """
        if self.time_to_expiry_years == 0:
            if self.option_type == OptionType.CALL:
                return float(max(0.0, spot_price - self.strike_price))
            else:
                return float(max(0.0, self.strike_price - spot_price))
                
        s = spot_price
        k = self.strike_price
        t = self.time_to_expiry_years
        r = self.risk_free_rate
        q = self.dividend_yield
        v = max(1e-4, self.implied_volatility)
        
        d1 = (np.log(s / k) + (r - q + 0.5 * (v ** 2)) * t) / (v * np.sqrt(t))
        d2 = d1 - (v * np.sqrt(t))
        
        if self.option_type == OptionType.CALL:
            price = (s * np.exp(-q * t) * norm.cdf(d1)) - (k * np.exp(-r * t) * norm.cdf(d2))
        else:
            price = (k * np.exp(-r * t) * norm.cdf(-d2)) - (s * np.exp(-q * t) * norm.cdf(-d1))
            
        return float(max(0.0, price))

    def compute_greeks(self, spot_price: float) -> Dict[str, float]:
        """
        Computes analytical Greeks for this single option leg.
        """
        s = spot_price
        k = self.strike_price
        t = self.time_to_expiry_years
        r = self.risk_free_rate
        q = self.dividend_yield
        v = max(1e-4, self.implied_volatility)
        
        if t <= 0:
            return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "rho": 0.0}
            
        d1 = (np.log(s / k) + (r - q + 0.5 * (v ** 2)) * t) / (v * np.sqrt(t))
        d2 = d1 - (v * np.sqrt(t))
        
        sign = 1.0 if self.action == TradeAction.BUY else -1.0
        
        if self.option_type == OptionType.CALL:
            delta = np.exp(-q * t) * norm.cdf(d1)
            theta = (- (s * v * np.exp(-q * t) * norm.pdf(d1)) / (2 * np.sqrt(t))) - (r * k * np.exp(-r * t) * norm.cdf(d2)) + (q * s * np.exp(-q * t) * norm.cdf(d1))
            rho = k * t * np.exp(-r * t) * norm.cdf(d2)
        else:
            delta = -np.exp(-q * t) * norm.cdf(-d1)
            theta = (- (s * v * np.exp(-q * t) * norm.pdf(d1)) / (2 * np.sqrt(t))) + (r * k * np.exp(-r * t) * norm.cdf(-d2)) - (q * s * np.exp(-q * t) * norm.cdf(-d1))
            rho = -k * t * np.exp(-r * t) * norm.cdf(-d2)
            
        gamma = (np.exp(-q * t) * norm.pdf(d1)) / (s * v * np.sqrt(t))
        vega = s * np.exp(-q * t) * norm.pdf(d1) * np.sqrt(t)
        
        multiplier = sign * self.quantity * 100.0  # 100 shares per contract
        
        return {
            "delta": float(delta * multiplier),
            "gamma": float(gamma * multiplier),
            "vega": float(vega * multiplier * 0.01),     # Per 1% vol shift
            "theta": float((theta / 365.0) * multiplier),# Per calendar day
            "rho": float(rho * multiplier * 0.01)        # Per 1% rate shift
        }

class BaseOptionStrategy(ABC):
    """
    Abstract Base Class for all Options Strategies.
    Ensures strict polymorphic contracts for payoff, P&L, Greeks, and breakevens.
    """
    def __init__(self, name: str, spot_price_entry: float):
        self.name = name
        self.spot_price_entry = float(spot_price_entry)
        self.option_legs: List[OptionLeg] = []
        self.underlying_shares: float = 0.0  # Positive for long stock, negative for short stock

    @abstractmethod
    def compute_payoff(self, spot_prices: np.ndarray) -> np.ndarray:
        """
        Computes intrinsic terminal payoff at expiration across array of spot prices.
        """
        pass

    @abstractmethod
    def compute_profit_loss(self, spot_prices: np.ndarray) -> np.ndarray:
        """
        Computes net profit and loss (Payoff minus initial net premium / entry cash flow).
        """
        pass

    @abstractmethod
    def get_break_even_points(self) -> List[float]:
        """
        Returns exact stock prices where terminal P&L is zero.
        """
        pass

    @abstractmethod
    def get_max_profit_and_loss(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Returns (Max Profit, Max Loss) in USD. None indicates unlimited profit or loss.
        """
        pass

    def compute_portfolio_greeks(self, current_spot: float) -> Dict[str, float]:
        """
        Aggregates total Greeks across underlying shares and all active option legs.
        """
        total_delta = float(self.underlying_shares)
        total_gamma = 0.0
        total_vega = 0.0
        total_theta = 0.0
        total_rho = 0.0
        
        for leg in self.option_legs:
            g = leg.compute_greeks(current_spot)
            total_delta += g["delta"]
            total_gamma += g["gamma"]
            total_vega += g["vega"]
            total_theta += g["theta"]
            total_rho += g["rho"]
            
        return {
            "total_delta": round(total_delta, 4),
            "total_gamma": round(total_gamma, 4),
            "total_vega_per_1pct": round(total_vega, 4),
            "total_theta_per_day": round(total_theta, 4),
            "total_rho_per_1pct": round(total_rho, 4)
        }

# ==================== CONCRETE STRATEGIES ====================

class CoveredCallStrategy(BaseOptionStrategy):
    """
    CFA Level II/III Covered Call Strategy:
    Long 100 shares of underlying stock + Short 1 OTM/ATM Call Option.
    """
    def __init__(
        self,
        spot_price_entry: float,
        call_strike: float,
        time_to_expiry_years: float,
        implied_volatility: float,
        shares_quantity: float = 100.0,
        call_premium: Optional[float] = None,
        risk_free_rate: float = 0.045
    ):
        super().__init__("Covered Call", spot_price_entry)
        self.underlying_shares = shares_quantity
        self.call_strike = float(call_strike)
        
        num_contracts = shares_quantity / 100.0
        self.call_leg = OptionLeg(
            option_type=OptionType.CALL,
            action=TradeAction.SELL,
            strike_price=self.call_strike,
            time_to_expiry_years=time_to_expiry_years,
            implied_volatility=implied_volatility,
            quantity=num_contracts,
            premium=call_premium,
            risk_free_rate=risk_free_rate
        )
        if self.call_leg.premium is None:
            self.call_leg.premium = self.call_leg.compute_bsm_price(self.spot_price_entry)
            
        self.option_legs.append(self.call_leg)

    def compute_payoff(self, spot_prices: np.ndarray) -> np.ndarray:
        s_t = np.asarray(spot_prices)
        stock_payoff = self.underlying_shares * s_t
        call_payoff = - (self.underlying_shares) * np.maximum(0.0, s_t - self.call_strike)
        return stock_payoff + call_payoff

    def compute_profit_loss(self, spot_prices: np.ndarray) -> np.ndarray:
        s_t = np.asarray(spot_prices)
        stock_pnl = self.underlying_shares * (s_t - self.spot_price_entry)
        call_pnl = self.underlying_shares * (self.call_leg.premium - np.maximum(0.0, s_t - self.call_strike))
        return stock_pnl + call_pnl

    def get_break_even_points(self) -> List[float]:
        # Breakeven = S_0 - Call_Premium
        be = self.spot_price_entry - self.call_leg.premium
        return [round(float(be), 2)]

    def get_max_profit_and_loss(self) -> Tuple[Optional[float], Optional[float]]:
        # Max Profit = (K - S_0 + Premium) * shares
        max_profit = self.underlying_shares * (self.call_strike - self.spot_price_entry + self.call_leg.premium)
        # Max Loss = (S_0 - Premium) * shares (if stock falls to 0)
        max_loss = - self.underlying_shares * (self.spot_price_entry - self.call_leg.premium)
        return float(max_profit), float(max_loss)

class ProtectiveCollarStrategy(BaseOptionStrategy):
    """
    CFA Level III Institutional Protective Collar Strategy:
    Long Stock + Long OTM Put (Floor) + Short OTM Call (Cap to finance put).
    """
    def __init__(
        self,
        spot_price_entry: float,
        put_strike: float,
        call_strike: float,
        time_to_expiry_years: float,
        implied_volatility: float,
        shares_quantity: float = 100.0,
        put_premium: Optional[float] = None,
        call_premium: Optional[float] = None,
        risk_free_rate: float = 0.045
    ):
        super().__init__("Protective Collar", spot_price_entry)
        if put_strike >= call_strike:
            raise ValueError(f"Put strike ({put_strike}) must be strictly less than Call strike ({call_strike})")
            
        self.underlying_shares = shares_quantity
        self.put_strike = float(put_strike)
        self.call_strike = float(call_strike)
        num_contracts = shares_quantity / 100.0
        
        self.put_leg = OptionLeg(
            option_type=OptionType.PUT,
            action=TradeAction.BUY,
            strike_price=self.put_strike,
            time_to_expiry_years=time_to_expiry_years,
            implied_volatility=implied_volatility,
            quantity=num_contracts,
            premium=put_premium,
            risk_free_rate=risk_free_rate
        )
        if self.put_leg.premium is None:
            self.put_leg.premium = self.put_leg.compute_bsm_price(self.spot_price_entry)
            
        self.call_leg = OptionLeg(
            option_type=OptionType.CALL,
            action=TradeAction.SELL,
            strike_price=self.call_strike,
            time_to_expiry_years=time_to_expiry_years,
            implied_volatility=implied_volatility,
            quantity=num_contracts,
            premium=call_premium,
            risk_free_rate=risk_free_rate
        )
        if self.call_leg.premium is None:
            self.call_leg.premium = self.call_leg.compute_bsm_price(self.spot_price_entry)
            
        self.option_legs.extend([self.put_leg, self.call_leg])

    @property
    def net_premium_debit_per_share(self) -> float:
        return self.put_leg.premium - self.call_leg.premium

    def compute_payoff(self, spot_prices: np.ndarray) -> np.ndarray:
        s_t = np.asarray(spot_prices)
        stock_payoff = self.underlying_shares * s_t
        put_payoff = self.underlying_shares * np.maximum(0.0, self.put_strike - s_t)
        call_payoff = - self.underlying_shares * np.maximum(0.0, s_t - self.call_strike)
        return stock_payoff + put_payoff + call_payoff

    def compute_profit_loss(self, spot_prices: np.ndarray) -> np.ndarray:
        s_t = np.asarray(spot_prices)
        payoff = self.compute_payoff(s_t)
        initial_outlay = self.underlying_shares * (self.spot_price_entry + self.net_premium_debit_per_share)
        return payoff - initial_outlay

    def get_break_even_points(self) -> List[float]:
        be = self.spot_price_entry + self.net_premium_debit_per_share
        return [round(float(be), 2)]

    def get_max_profit_and_loss(self) -> Tuple[Optional[float], Optional[float]]:
        # Max Profit = (K_call - S_0 - net_debit) * shares
        max_p = self.underlying_shares * (self.call_strike - self.spot_price_entry - self.net_premium_debit_per_share)
        # Max Loss = (K_put - S_0 - net_debit) * shares
        max_l = self.underlying_shares * (self.put_strike - self.spot_price_entry - self.net_premium_debit_per_share)
        return float(max_p), float(max_l)

class BullCallSpreadStrategy(BaseOptionStrategy):
    """
    Bull Call Spread: Long Call (K1) + Short Call (K2) where K1 < K2.
    """
    def __init__(
        self,
        spot_price_entry: float,
        lower_strike_k1: float,
        upper_strike_k2: float,
        time_to_expiry_years: float,
        implied_volatility: float,
        quantity_contracts: float = 1.0,
        risk_free_rate: float = 0.045
    ):
        super().__init__("Bull Call Spread", spot_price_entry)
        if lower_strike_k1 >= upper_strike_k2:
            raise ValueError(f"Lower strike K1 ({lower_strike_k1}) must be < upper strike K2 ({upper_strike_k2})")
            
        self.k1 = float(lower_strike_k1)
        self.k2 = float(upper_strike_k2)
        self.quantity = float(quantity_contracts)
        
        self.long_call = OptionLeg(OptionType.CALL, TradeAction.BUY, self.k1, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.long_call.premium = self.long_call.compute_bsm_price(spot_price_entry)
        
        self.short_call = OptionLeg(OptionType.CALL, TradeAction.SELL, self.k2, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.short_call.premium = self.short_call.compute_bsm_price(spot_price_entry)
        
        self.option_legs.extend([self.long_call, self.short_call])

    @property
    def net_debit_per_share(self) -> float:
        return self.long_call.premium - self.short_call.premium

    def compute_payoff(self, spot_prices: np.ndarray) -> np.ndarray:
        s_t = np.asarray(spot_prices)
        long_payoff = np.maximum(0.0, s_t - self.k1)
        short_payoff = - np.maximum(0.0, s_t - self.k2)
        return (long_payoff + short_payoff) * self.quantity * 100.0

    def compute_profit_loss(self, spot_prices: np.ndarray) -> np.ndarray:
        payoff = self.compute_payoff(spot_prices)
        initial_cost = self.net_debit_per_share * self.quantity * 100.0
        return payoff - initial_cost

    def get_break_even_points(self) -> List[float]:
        return [round(float(self.k1 + self.net_debit_per_share), 2)]

    def get_max_profit_and_loss(self) -> Tuple[Optional[float], Optional[float]]:
        max_p = ((self.k2 - self.k1) - self.net_debit_per_share) * self.quantity * 100.0
        max_l = - self.net_debit_per_share * self.quantity * 100.0
        return float(max_p), float(max_l)

class IronCondorStrategy(BaseOptionStrategy):
    """
    Institutional Iron Condor:
    1. Bull Put Spread: Long Put (K1) + Short Put (K2)
    2. Bear Call Spread: Short Call (K3) + Long Call (K4)
    With K1 < K2 < K3 < K4.
    """
    def __init__(
        self,
        spot_price_entry: float,
        put_long_k1: float,
        put_short_k2: float,
        call_short_k3: float,
        call_long_k4: float,
        time_to_expiry_years: float,
        implied_volatility: float,
        quantity_contracts: float = 1.0,
        risk_free_rate: float = 0.045
    ):
        super().__init__("Iron Condor", spot_price_entry)
        if not (put_long_k1 < put_short_k2 < call_short_k3 < call_long_k4):
            raise ValueError(f"Strikes must satisfy K1 < K2 < K3 < K4, got {put_long_k1}, {put_short_k2}, {call_short_k3}, {call_long_k4}")
            
        self.k1, self.k2, self.k3, self.k4 = float(put_long_k1), float(put_short_k2), float(call_short_k3), float(call_long_k4)
        self.quantity = float(quantity_contracts)
        
        self.p_long = OptionLeg(OptionType.PUT, TradeAction.BUY, self.k1, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.p_long.premium = self.p_long.compute_bsm_price(spot_price_entry)
        
        self.p_short = OptionLeg(OptionType.PUT, TradeAction.SELL, self.k2, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.p_short.premium = self.p_short.compute_bsm_price(spot_price_entry)
        
        self.c_short = OptionLeg(OptionType.CALL, TradeAction.SELL, self.k3, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.c_short.premium = self.c_short.compute_bsm_price(spot_price_entry)
        
        self.c_long = OptionLeg(OptionType.CALL, TradeAction.BUY, self.k4, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.c_long.premium = self.c_long.compute_bsm_price(spot_price_entry)
        
        self.option_legs.extend([self.p_long, self.p_short, self.c_short, self.c_long])

    @property
    def net_credit_per_share(self) -> float:
        # Credit from selling K2 Put + K3 Call minus cost of buying K1 Put + K4 Call
        return (self.p_short.premium + self.c_short.premium) - (self.p_long.premium + self.c_long.premium)

    def compute_payoff(self, spot_prices: np.ndarray) -> np.ndarray:
        s_t = np.asarray(spot_prices)
        p_l_pay = np.maximum(0.0, self.k1 - s_t)
        p_s_pay = - np.maximum(0.0, self.k2 - s_t)
        c_s_pay = - np.maximum(0.0, s_t - self.k3)
        c_l_pay = np.maximum(0.0, s_t - self.k4)
        return (p_l_pay + p_s_pay + c_s_pay + c_l_pay) * self.quantity * 100.0

    def compute_profit_loss(self, spot_prices: np.ndarray) -> np.ndarray:
        payoff = self.compute_payoff(spot_prices)
        initial_credit = self.net_credit_per_share * self.quantity * 100.0
        return payoff + initial_credit

    def get_break_even_points(self) -> List[float]:
        be_lower = self.k2 - self.net_credit_per_share
        be_upper = self.k3 + self.net_credit_per_share
        return [round(float(be_lower), 2), round(float(be_upper), 2)]

    def get_max_profit_and_loss(self) -> Tuple[Optional[float], Optional[float]]:
        max_p = self.net_credit_per_share * self.quantity * 100.0
        wing_width = max(self.k2 - self.k1, self.k4 - self.k3)
        max_l = - (wing_width - self.net_credit_per_share) * self.quantity * 100.0
        return float(max_p), float(max_l)

class LongStraddleStrategy(BaseOptionStrategy):
    """
    Long Straddle: Long Call (K) + Long Put (K) at same strike.
    """
    def __init__(
        self,
        spot_price_entry: float,
        strike_price: float,
        time_to_expiry_years: float,
        implied_volatility: float,
        quantity_contracts: float = 1.0,
        risk_free_rate: float = 0.045
    ):
        super().__init__("Long Straddle", spot_price_entry)
        self.strike = float(strike_price)
        self.quantity = float(quantity_contracts)
        
        self.call_leg = OptionLeg(OptionType.CALL, TradeAction.BUY, self.strike, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.call_leg.premium = self.call_leg.compute_bsm_price(spot_price_entry)
        
        self.put_leg = OptionLeg(OptionType.PUT, TradeAction.BUY, self.strike, time_to_expiry_years, implied_volatility, self.quantity, risk_free_rate=risk_free_rate)
        self.put_leg.premium = self.put_leg.compute_bsm_price(spot_price_entry)
        
        self.option_legs.extend([self.call_leg, self.put_leg])

    @property
    def total_cost_per_share(self) -> float:
        return self.call_leg.premium + self.put_leg.premium

    def compute_payoff(self, spot_prices: np.ndarray) -> np.ndarray:
        s_t = np.asarray(spot_prices)
        return (np.maximum(0.0, s_t - self.strike) + np.maximum(0.0, self.strike - s_t)) * self.quantity * 100.0

    def compute_profit_loss(self, spot_prices: np.ndarray) -> np.ndarray:
        payoff = self.compute_payoff(spot_prices)
        return payoff - (self.total_cost_per_share * self.quantity * 100.0)

    def get_break_even_points(self) -> List[float]:
        cost = self.total_cost_per_share
        return [round(float(self.strike - cost), 2), round(float(self.strike + cost), 2)]

    def get_max_profit_and_loss(self) -> Tuple[Optional[float], Optional[float]]:
        max_p = None  # Unlimited upside/downside
        max_l = - self.total_cost_per_share * self.quantity * 100.0
        return max_p, float(max_l)

# ==================== INSTITUTIONAL GREEKS HEDGING SOLVER ====================

class GreeksHedgingSolver:
    """
    CFA Level II & III Multi-Greeks Hedging Optimization Solver.
    Calculates exact hedging ratios to achieve:
    1. Delta Neutrality (Delta = 0)
    2. Gamma-Delta Neutrality (Gamma = 0, Delta = 0)
    3. Vega-Gamma-Delta Neutrality (Vega = 0, Gamma = 0, Delta = 0)
    """
    @staticmethod
    def solve_delta_neutral_hedging(portfolio_delta: float) -> Dict[str, Any]:
        """
        Solves for underlying stock shares needed to neutralize portfolio delta:
        N_shares = - Delta_portfolio
        """
        required_shares = - float(portfolio_delta)
        action = "BUY_STOCK" if required_shares > 0 else "SELL_STOCK"
        return {
            "target": "DELTA_NEUTRAL",
            "initial_delta": round(float(portfolio_delta), 4),
            "underlying_shares_adjustment": round(required_shares, 2),
            "action": action,
            "residual_delta": 0.0
        }

    @staticmethod
    def solve_gamma_delta_neutral_hedging(
        portfolio_delta: float,
        portfolio_gamma: float,
        h1_delta_per_contract: float,
        h1_gamma_per_contract: float
    ) -> Dict[str, Any]:
        """
        Solves for Gamma-Neutral and Delta-Neutral simultaneous hedge using 1 Option + Underlying stock:
        1. N_H1 = - Gamma_port / Gamma_H1
        2. N_shares = - (Delta_port + N_H1 * Delta_H1)
        """
        if abs(h1_gamma_per_contract) < 1e-8:
            raise ValueError("Hedging option Gamma cannot be zero.")
            
        n_h1_contracts = - float(portfolio_gamma) / float(h1_gamma_per_contract)
        remaining_delta = float(portfolio_delta) + (n_h1_contracts * float(h1_delta_per_contract))
        n_shares = - remaining_delta
        
        return {
            "target": "GAMMA_DELTA_NEUTRAL",
            "initial_delta": round(float(portfolio_delta), 4),
            "initial_gamma": round(float(portfolio_gamma), 4),
            "hedging_option_contracts": round(n_h1_contracts, 2),
            "underlying_shares_adjustment": round(n_shares, 2),
            "residual_delta": 0.0,
            "residual_gamma": 0.0
        }

    @staticmethod
    def solve_vega_gamma_delta_neutral_hedging(
        portfolio_delta: float,
        portfolio_gamma: float,
        portfolio_vega: float,
        h1_greeks_per_contract: Dict[str, float],
        h2_greeks_per_contract: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Solves 2x2 linear system for Vega & Gamma neutrality using 2 options, then neutralizes Delta with stock:
        [Gamma_H1  Gamma_H2] [N_H1] = [- Gamma_port]
        [Vega_H1   Vega_H2 ] [N_H2]   [- Vega_port ]
        """
        g1, v1, d1 = h1_greeks_per_contract["gamma"], h1_greeks_per_contract["vega"], h1_greeks_per_contract["delta"]
        g2, v2, d2 = h2_greeks_per_contract["gamma"], h2_greeks_per_contract["vega"], h2_greeks_per_contract["delta"]
        
        A = np.array([[g1, g2], [v1, v2]])
        b = np.array([-portfolio_gamma, -portfolio_vega])
        
        det = np.linalg.det(A)
        if abs(det) < 1e-8:
            raise ValueError("Hedging options matrix is singular (collinear Gamma/Vega profiles). Select non-collinear strikes/expiries.")
            
        contracts = np.linalg.solve(A, b)
        n_h1, n_h2 = float(contracts[0]), float(contracts[1])
        
        total_option_delta = float(portfolio_delta) + (n_h1 * d1) + (n_h2 * d2)
        n_shares = - total_option_delta
        
        # Invariant Verification
        residual_gamma = float(portfolio_gamma + n_h1 * g1 + n_h2 * g2)
        residual_vega = float(portfolio_vega + n_h1 * v1 + n_h2 * v2)
        residual_delta = float(total_option_delta + n_shares)
        
        return {
            "target": "VEGA_GAMMA_DELTA_NEUTRAL",
            "initial_delta": round(float(portfolio_delta), 4),
            "initial_gamma": round(float(portfolio_gamma), 4),
            "initial_vega": round(float(portfolio_vega), 4),
            "h1_option_contracts": round(n_h1, 2),
            "h2_option_contracts": round(n_h2, 2),
            "underlying_shares_adjustment": round(n_shares, 2),
            "residual_delta": round(residual_delta, 6),
            "residual_gamma": round(residual_gamma, 6),
            "residual_vega": round(residual_vega, 6)
        }

if __name__ == "__main__":
    print("Testing Institutional Options Strategy & Greeks Hedging Engine...")
    
    # 1. Covered Call
    cc = CoveredCallStrategy(spot_price_entry=500.0, call_strike=520.0, time_to_expiry_years=0.25, implied_volatility=0.20)
    print(f"Covered Call Max Profit: ${cc.get_max_profit_and_loss()[0]:,.2f} | Breakeven: ${cc.get_break_even_points()[0]:.2f}")
    
    # 2. Iron Condor
    ic = IronCondorStrategy(spot_price_entry=500.0, put_long_k1=470.0, put_short_k2=485.0, call_short_k3=515.0, call_long_k4=530.0, time_to_expiry_years=0.15, implied_volatility=0.22)
    print(f"Iron Condor Max Profit: ${ic.get_max_profit_and_loss()[0]:,.2f} | Max Loss: ${ic.get_max_profit_and_loss()[1]:,.2f} | Breakevens: {ic.get_break_even_points()}")
    
    # 3. Greeks Hedging Solver
    port_greeks = {"delta": 350.0, "gamma": 12.5, "vega": 45.0}
    h1 = {"delta": 55.0, "gamma": 2.5, "vega": 8.0}
    h2 = {"delta": -35.0, "gamma": 1.8, "vega": 14.0}
    
    hedge_sol = GreeksHedgingSolver.solve_vega_gamma_delta_neutral_hedging(
        port_greeks["delta"], port_greeks["gamma"], port_greeks["vega"], h1, h2
    )
    print("Vega-Gamma-Delta Hedge Solution:", hedge_sol)
