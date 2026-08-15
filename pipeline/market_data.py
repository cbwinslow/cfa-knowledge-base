#!/usr/bin/env python3
"""
Market Data & Risk-Free Rate Client
Fetches live market capitalization, beta, shares outstanding, current price,
and the 10-Year US Treasury Yield (Risk-Free Rate).
"""

import yfinance as yf
from typing import Dict, Any, Optional

class MarketDataClient:
    def __init__(self):
        self._rf_rate_cache: Optional[float] = None

    def get_risk_free_rate(self) -> float:
        """
        Fetches the 10-Year US Treasury Yield (^TNX). Defaults to 4.25% if market is closed.
        """
        if self._rf_rate_cache is not None:
            return self._rf_rate_cache

        try:
            tnx = yf.Ticker("^TNX")
            hist = tnx.history(period="5d")
            if not hist.empty:
                val = float(hist["Close"].iloc[-1]) / 100.0
                if 0.01 <= val <= 0.15:
                    self._rf_rate_cache = val
                    return val
        except Exception:
            pass

        self._rf_rate_cache = 0.0425  # Standard 4.25% baseline
        return self._rf_rate_cache

    def get_market_quote(self, ticker: str) -> Dict[str, Any]:
        """
        Retrieves current price, market cap, shares outstanding, and beta.
        """
        t = yf.Ticker(ticker)
        info = t.info or {}
        
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose") or 0.0
        shares = info.get("sharesOutstanding") or 0
        market_cap = info.get("marketCap") or (current_price * shares)
        beta = info.get("beta") or 1.0
        sector = info.get("sector") or "General"
        industry = info.get("industry") or "General"

        return {
            "ticker": ticker.upper(),
            "current_price": float(current_price),
            "market_cap": float(market_cap),
            "shares_outstanding": int(shares),
            "beta": float(beta),
            "sector": sector,
            "industry": industry,
            "risk_free_rate": self.get_risk_free_rate()
        }

if __name__ == "__main__":
    client = MarketDataClient()
    print("Testing Market Data Client for MSFT...")
    data = client.get_market_quote("MSFT")
    print(f"Ticker: {data['ticker']}")
    print(f"Current Price: ${data['current_price']:,.2f}")
    print(f"Market Cap: ${data['market_cap']:,.0f}")
    print(f"Beta: {data['beta']:.2f}")
    print(f"10-Yr US Treasury (Rf): {data['risk_free_rate']*100:.2f}%")
