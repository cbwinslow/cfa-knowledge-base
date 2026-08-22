"""
Options Analytics Engine: Black-Scholes Greeks, Implied Volatility, Skew, and PCR.
Supports vectorized NumPy arrays and Pandas DataFrames.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Union, Dict, Any
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

@dataclass(frozen=True)
class GreekResults:
    price: np.ndarray
    delta: np.ndarray
    gamma: np.ndarray
    vega: np.ndarray
    vega_1pct: np.ndarray
    theta: np.ndarray
    theta_1d: np.ndarray
    rho: np.ndarray
    vanna: np.ndarray
    volga: np.ndarray
    dollar_delta: np.ndarray
    dollar_gamma_1pct: np.ndarray

class OptionsAnalyticsEngine:
    def __init__(self, risk_free_rate_default: float = 0.0474, dividend_yield_default: float = 0.0):
        self.r_default = risk_free_rate_default
        self.q_default = dividend_yield_default

    def calculate_greeks(
        self,
        spot: Union[float, np.ndarray],
        strike: Union[float, np.ndarray],
        tte: Union[float, np.ndarray],
        volatility: Union[float, np.ndarray],
        risk_free_rate: Optional[Union[float, np.ndarray]] = None,
        dividend_yield: Optional[Union[float, np.ndarray]] = None,
        flag: Union[str, np.ndarray] = 'call'
    ) -> GreekResults:
        r = self.r_default if risk_free_rate is None else risk_free_rate
        q = self.q_default if dividend_yield is None else dividend_yield

        S = np.asarray(spot, dtype=np.float64)
        K = np.asarray(strike, dtype=np.float64)
        T = np.maximum(np.asarray(tte, dtype=np.float64), 1e-6)
        sigma = np.maximum(np.asarray(volatility, dtype=np.float64), 1e-6)
        r = np.asarray(r, dtype=np.float64)
        q = np.asarray(q, dtype=np.float64)

        if isinstance(flag, str):
            is_call = np.full(S.shape, 1 if flag.lower() in ('c', 'call') else -1, dtype=np.int8)
        else:
            is_call = np.where(np.isin(np.asarray(flag), ['c', 'C', 'call', 'CALL', 1]), 1, -1).astype(np.int8)

        S, K, T, sigma, r, q, is_call = np.broadcast_arrays(S, K, T, sigma, r, q, is_call)

        sqrt_T = np.sqrt(T)
        vol_sqrt_T = sigma * sqrt_T
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / vol_sqrt_T
        d2 = d1 - vol_sqrt_T

        nd1 = norm.cdf(d1)
        nd2 = norm.cdf(d2)
        n_neg_d1 = norm.cdf(-d1)
        n_neg_d2 = norm.cdf(-d2)
        pdf_d1 = norm.pdf(d1)

        discount_r = np.exp(-r * T)
        discount_q = np.exp(-q * T)

        call_price = S * discount_q * nd1 - K * discount_r * nd2
        put_price = K * discount_r * n_neg_d2 - S * discount_q * n_neg_d1
        price = np.maximum(np.where(is_call == 1, call_price, put_price), 0.0)

        call_delta = discount_q * nd1
        put_delta = -discount_q * n_neg_d1
        delta = np.where(is_call == 1, call_delta, put_delta)

        gamma = (discount_q * pdf_d1) / (S * vol_sqrt_T)
        vega = S * discount_q * pdf_d1 * sqrt_T
        vega_1pct = vega * 0.01

        theta_common = -(S * discount_q * pdf_d1 * sigma) / (2.0 * sqrt_T)
        call_theta = theta_common - r * K * discount_r * nd2 + q * S * discount_q * nd1
        put_theta = theta_common + r * K * discount_r * n_neg_d2 - q * S * discount_q * n_neg_d1
        theta = np.where(is_call == 1, call_theta, put_theta)
        theta_1d = theta / 365.0

        call_rho = K * T * discount_r * nd2 * 0.01
        put_rho = -K * T * discount_r * n_neg_d2 * 0.01
        rho = np.where(is_call == 1, call_rho, put_rho)

        vanna = -discount_q * pdf_d1 * (d2 / sigma)
        volga = vega * (d1 * d2 / sigma)

        dollar_delta = delta * S
        dollar_gamma_1pct = 0.5 * gamma * ((S * 0.01) ** 2)

        return GreekResults(
            price=price,
            delta=delta,
            gamma=gamma,
            vega=vega,
            vega_1pct=vega_1pct,
            theta=theta,
            theta_1d=theta_1d,
            rho=rho,
            vanna=vanna,
            volga=volga,
            dollar_delta=dollar_delta,
            dollar_gamma_1pct=dollar_gamma_1pct
        )

    def calculate_implied_volatility(
        self,
        price: Union[float, np.ndarray],
        spot: Union[float, np.ndarray],
        strike: Union[float, np.ndarray],
        tte: Union[float, np.ndarray],
        flag: Union[str, np.ndarray] = 'call'
    ) -> np.ndarray:
        P = np.asarray(price, dtype=np.float64)
        S = np.asarray(spot, dtype=np.float64)
        K = np.asarray(strike, dtype=np.float64)
        T = np.maximum(np.asarray(tte, dtype=np.float64), 1e-6)

        iv = np.zeros_like(P)
        for idx in range(len(P.flat)):
            p_val = P.flat[idx]
            s_val = S.flat[idx]
            k_val = K.flat[idx]
            t_val = T.flat[idx]
            f_val = flag if isinstance(flag, str) else flag.flat[idx]

            def obj(vol):
                res = self.calculate_greeks(s_val, k_val, t_val, vol, flag=f_val)
                return float(res.price) - p_val

            try:
                iv.flat[idx] = brentq(obj, 1e-4, 5.0, maxiter=50, xtol=1e-5)
            except Exception:
                iv.flat[idx] = np.nan
        return iv
