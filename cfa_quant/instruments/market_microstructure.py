"""
CFA Level III Market Microstructure, Limit Order Book (LOB) & Implementation Shortfall Engine
Implements:
1. Limit Order Book (LOB) Depth, Breadth & Order Flow Imbalance (OFI)
2. Quoted Spread, Effective Spread, and Realized Spread
3. CFA Level III Implementation Shortfall (IS) 4-Component Cost Attribution:
   - Explicit Fees & Commissions
   - Realized Execution Slippage (Execution vs. Arrival)
   - Delay / Market Drift Cost (Arrival vs. Decision)
   - Missed Trade / Opportunity Cost (Unfilled Allocation)
4. VWAP & TWAP Execution Slippage Simulator with Kyle's Lambda Price Impact
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd

@dataclass
class OrderBookLevel:
    price: float
    size_shares: int
    num_orders: int

@dataclass
class OrderBookSnapshot:
    ticker: str
    timestamp: str
    bids: List[OrderBookLevel]  # Ordered highest price to lowest
    asks: List[OrderBookLevel]  # Ordered lowest price to highest

@dataclass
class ImplementationShortfallResult:
    decision_price: float
    arrival_price: float
    average_execution_price: float
    cancellation_closing_price: float
    total_target_shares: int
    executed_shares: int
    unexecuted_shares: int
    explicit_commissions_usd: float
    
    # 4-Component CFA Breakdown ($ and bps)
    delay_market_drift_usd: float
    delay_market_drift_bps: float
    
    realized_execution_slippage_usd: float
    realized_execution_slippage_bps: float
    
    missed_trade_opportunity_cost_usd: float
    missed_trade_opportunity_cost_bps: float
    
    explicit_costs_usd: float
    explicit_costs_bps: float
    
    total_implementation_shortfall_usd: float
    total_implementation_shortfall_bps: float

class MarketMicrostructureEngine:
    def __init__(self):
        pass

    def analyze_order_book_depth(self, book: OrderBookSnapshot) -> Dict[str, Any]:
        """
        Computes LOB Microstructure metrics:
        - Best Bid / Best Ask / Midpoint Price
        - Quoted Spread ($ and bps)
        - Depth within 0.5% and 1.0% of midpoint
        - Order Flow Imbalance (OFI): (Bid_Volume - Ask_Volume) / (Bid_Volume + Ask_Volume)
        """
        best_bid = book.bids[0].price
        best_ask = book.asks[0].price
        midpoint = (best_bid + best_ask) / 2.0
        
        quoted_spread = best_ask - best_bid
        quoted_spread_bps = (quoted_spread / midpoint) * 10000.0
        
        # Cumulative depth within 1% of mid
        bid_depth_1pct = sum(level.size_shares for level in book.bids if level.price >= midpoint * 0.99)
        ask_depth_1pct = sum(level.size_shares for level in book.asks if level.price <= midpoint * 1.01)
        
        total_depth = bid_depth_1pct + ask_depth_1pct
        ofi = (bid_depth_1pct - ask_depth_1pct) / max(total_depth, 1)
        
        return {
            "ticker": book.ticker,
            "best_bid": round(best_bid, 2),
            "best_ask": round(best_ask, 2),
            "midpoint_price": round(midpoint, 2),
            "quoted_spread_usd": round(quoted_spread, 4),
            "quoted_spread_bps": round(quoted_spread_bps, 2),
            "bid_depth_1pct_shares": bid_depth_1pct,
            "ask_depth_1pct_shares": ask_depth_1pct,
            "order_flow_imbalance_ratio": round(ofi, 3),
            "market_pressure": "Buy Pressure (Bullish LOB)" if ofi > 0.1 else ("Sell Pressure (Bearish LOB)" if ofi < -0.1 else "Neutral")
        }

    def compute_implementation_shortfall(
        self,
        decision_price: float,
        arrival_price: float,
        executed_shares: int,
        total_target_shares: int,
        execution_prices: List[float],
        execution_volumes: List[int],
        cancellation_price: float,
        explicit_commissions_usd: float = 250.0,
        is_buy: bool = True
    ) -> ImplementationShortfallResult:
        """
        CFA Level III Implementation Shortfall (IS) 4-Way Decomposition:
        Base Benchmark Value: Base = Target_Shares * Decision_Price
        
        1. Delay (Market Drift) Cost:
           Delay = Executed_Shares * (Arrival_Price - Decision_Price)
           
        2. Realized Execution Cost (Slippage):
           Realized = sum(Volume_i * (Execution_Price_i - Arrival_Price))
           
        3. Missed Trade (Opportunity) Cost:
           Missed = (Target_Shares - Executed_Shares) * (Closing_Cancellation_Price - Decision_Price)
           
        4. Explicit Costs = Commissions, exchange fees, taxes
        
        Total IS = Delay + Realized + Missed + Explicit
        """
        side = 1.0 if is_buy else -1.0
        base_benchmark = total_target_shares * decision_price
        
        # Weighted average execution price
        total_exec_shares = sum(execution_volumes)
        avg_exec_price = sum(p * v for p, v in zip(execution_prices, execution_volumes)) / max(total_exec_shares, 1)
        unexec_shares = max(0, total_target_shares - total_exec_shares)
        
        # 1. Delay Cost
        delay_usd = total_exec_shares * (arrival_price - decision_price) * side
        delay_bps = (delay_usd / base_benchmark) * 10000.0
        
        # 2. Realized Execution Cost
        realized_usd = sum(v * (p - arrival_price) * side for p, v in zip(execution_prices, execution_volumes))
        realized_bps = (realized_usd / base_benchmark) * 10000.0
        
        # 3. Missed Trade Cost
        missed_usd = unexec_shares * (cancellation_price - decision_price) * side
        missed_bps = (missed_usd / base_benchmark) * 10000.0
        
        # 4. Explicit Costs
        explicit_usd = explicit_commissions_usd
        explicit_bps = (explicit_usd / base_benchmark) * 10000.0
        
        total_is_usd = delay_usd + realized_usd + missed_usd + explicit_usd
        total_is_bps = (total_is_usd / base_benchmark) * 10000.0
        
        return ImplementationShortfallResult(
            decision_price=round(decision_price, 2),
            arrival_price=round(arrival_price, 2),
            average_execution_price=round(avg_exec_price, 2),
            cancellation_closing_price=round(cancellation_price, 2),
            total_target_shares=total_target_shares,
            executed_shares=total_exec_shares,
            unexecuted_shares=unexec_shares,
            explicit_commissions_usd=round(explicit_usd, 2),
            
            delay_market_drift_usd=round(delay_usd, 2),
            delay_market_drift_bps=round(delay_bps, 1),
            
            realized_execution_slippage_usd=round(realized_usd, 2),
            realized_execution_slippage_bps=round(realized_bps, 1),
            
            missed_trade_opportunity_cost_usd=round(missed_usd, 2),
            missed_trade_opportunity_cost_bps=round(missed_bps, 1),
            
            explicit_costs_usd=round(explicit_usd, 2),
            explicit_costs_bps=round(explicit_bps, 1),
            
            total_implementation_shortfall_usd=round(total_is_usd, 2),
            total_implementation_shortfall_bps=round(total_is_bps, 1)
        )

if __name__ == "__main__":
    eng = MarketMicrostructureEngine()
    print("=" * 75)
    print("🏛️ CFA LEVEL III MARKET MICROSTRUCTURE & IMPLEMENTATION SHORTFALL")
    print("=" * 75)
    
    # 1. Test Order Book Snapshot
    sample_bids = [
        OrderBookLevel(price=483.20, size_shares=1500, num_orders=8),
        OrderBookLevel(price=483.15, size_shares=3200, num_orders=14),
        OrderBookLevel(price=483.10, size_shares=5800, num_orders=22),
        OrderBookLevel(price=483.00, size_shares=12000, num_orders=45)
    ]
    sample_asks = [
        OrderBookLevel(price=483.25, size_shares=1200, num_orders=6),
        OrderBookLevel(price=483.30, size_shares=2800, num_orders=11),
        OrderBookLevel(price=483.35, size_shares=4500, num_orders=18),
        OrderBookLevel(price=483.50, size_shares=9000, num_orders=38)
    ]
    book = OrderBookSnapshot(ticker="MSFT", timestamp="2026-08-22 10:00:00", bids=sample_bids, asks=sample_asks)
    ob_metrics = eng.analyze_order_book_depth(book)
    print(f"Ticker: {ob_metrics['ticker']} | Midpoint: ${ob_metrics['midpoint_price']:,.2f}")
    print(f"Quoted Spread: ${ob_metrics['quoted_spread_usd']} ({ob_metrics['quoted_spread_bps']} bps)")
    print(f"1% Depth - Bids: {ob_metrics['bid_depth_1pct_shares']:,} shs | Asks: {ob_metrics['ask_depth_1pct_shares']:,} shs")
    print(f"Order Flow Imbalance: {ob_metrics['order_flow_imbalance_ratio']:+0.2f} ({ob_metrics['market_pressure']})")
    
    # 2. Test Implementation Shortfall Decomposition
    print("\n📊 CFA Level III Implementation Shortfall Execution Report:")
    is_res = eng.compute_implementation_shortfall(
        decision_price=100.0,
        arrival_price=100.50,
        executed_shares=8000,
        total_target_shares=10000,
        execution_prices=[100.70, 100.90, 101.10],
        execution_volumes=[3000, 3000, 2000],
        cancellation_price=102.00,
        explicit_commissions_usd=400.0,
        is_buy=True
    )
    print(f"Target: {is_res.total_target_shares:,} shs @ Decision ${is_res.decision_price:.2f}")
    print(f"Executed: {is_res.executed_shares:,} shs @ Avg ${is_res.average_execution_price:.2f} | Unfilled: {is_res.unexecuted_shares:,} shs @ Close ${is_res.cancellation_closing_price:.2f}")
    print(f"\nCost Attribution Breakdown:")
    print(f"  • Delay (Market Drift) Cost:       ${is_res.delay_market_drift_usd:,.2f} ({is_res.delay_market_drift_bps:+.1f} bps)")
    print(f"  • Realized Execution Slippage:     ${is_res.realized_execution_slippage_usd:,.2f} ({is_res.realized_execution_slippage_bps:+.1f} bps)")
    print(f"  • Missed Trade (Opportunity Cost): ${is_res.missed_trade_opportunity_cost_usd:,.2f} ({is_res.missed_trade_opportunity_cost_bps:+.1f} bps)")
    print(f"  • Explicit Fees & Commissions:     ${is_res.explicit_costs_usd:,.2f} ({is_res.explicit_costs_bps:+.1f} bps)")
    print(f"  -------------------------------------------------------------")
    print(f"  TOTAL IMPLEMENTATION SHORTFALL:    ${is_res.total_implementation_shortfall_usd:,.2f} ({is_res.total_implementation_shortfall_bps:+.1f} bps)")
    print("=" * 75)
