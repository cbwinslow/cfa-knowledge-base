"""
CFA Level II & III Walk-Forward Backtesting & Execution Slippage Simulator
Implements:
1. Multi-Asset Walk-Forward Strategy Simulator with Calendar vs. Dynamic Corridor Rebalancing
2. Institutional Execution Friction & Slippage Engine:
   - Half Bid-Ask Spread Cost
   - Fixed Ticket & Exchange Fees
   - Non-Linear Market Impact (Almgren-Chriss / Kyle's Lambda)
3. Advanced Institutional Performance Attribution & Risk Metrics:
   - Compound Annual Growth Rate (CAGR)
   - Annualized Volatility & Downside Deviation
   - Sharpe Ratio, Sortino Ratio, Calmar Ratio & Omega Ratio
   - Maximum Drawdown (MDD) & Underwater Duration
   - Annual Turnover & Cumulative Friction Drag (bps)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd

@dataclass
class BacktestTradeRecord:
    step_index: int
    date_label: str
    asset: str
    action: str
    shares: float
    price: float
    notional: float
    spread_cost: float
    market_impact_cost: float
    commission_cost: float
    total_friction: float

@dataclass
class BacktestReport:
    strategy_name: str
    initial_capital: float
    ending_capital: float
    total_return_pct: float
    cagr_pct: float
    annualized_volatility_pct: float
    downside_deviation_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    omega_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_steps: int
    total_turnover_usd: float
    total_friction_drag_usd: float
    total_friction_drag_bps: float
    equity_curve: List[float] = field(default_factory=list)
    drawdown_series: List[float] = field(default_factory=list)
    trade_records: List[BacktestTradeRecord] = field(default_factory=list)

class WalkForwardBacktester:
    """
    CFA Institutional Walk-Forward Multi-Asset Backtesting Engine.
    """
    def __init__(
        self,
        risk_free_rate: float = 0.045,
        half_spread_bps: float = 5.0,        # 5 bps half spread
        commission_rate_bps: float = 2.0,    # 2 bps broker fee
        market_impact_lambda: float = 0.001, # Non-linear market impact coefficient
        fixed_ticket_fee: float = 1.00       # $1 per ticket
    ):
        self.risk_free_rate = float(risk_free_rate)
        self.half_spread = float(half_spread_bps) / 10000.0
        self.commission_rate = float(commission_rate_bps) / 10000.0
        self.market_impact_lambda = float(market_impact_lambda)
        self.fixed_ticket_fee = float(fixed_ticket_fee)

    def run_backtest(
        self,
        strategy_name: str,
        asset_names: List[str],
        price_matrix: np.ndarray,            # Shape: (T_steps, N_assets)
        target_weights: np.ndarray,          # Shape: (N_assets,)
        initial_capital: float = 10000000.0, # $10M Default
        rebalance_corridor_pct: float = 0.03,# 3% tolerance band
        rebalance_frequency_steps: int = 21, # E.g., Monthly (21 trading days)
        daily_adv_usd: Optional[List[float]] = None # Average Daily Volume in USD
    ) -> BacktestReport:
        """
        Executes discrete-time walk-forward simulation across historical price matrix.
        """
        prices = np.asarray(price_matrix, dtype=float)
        t_steps, n_assets = prices.shape
        
        if len(asset_names) != n_assets or len(target_weights) != n_assets:
            raise ValueError(f"Asset count mismatch: prices have {n_assets} assets, provided {len(asset_names)} names, {len(target_weights)} weights.")
        if not np.isclose(np.sum(target_weights), 1.0, atol=1e-3):
            target_weights = target_weights / np.sum(target_weights)
            
        adv = daily_adv_usd or [50000000.0] * n_assets # Default $50M ADV
        
        # Initial Portfolio Allocation at Step 0
        current_holdings = np.zeros(n_assets) # Number of shares
        cash = float(initial_capital)
        trades: List[BacktestTradeRecord] = []
        equity_curve: List[float] = []
        
        # Initial Buy Order
        for i in range(n_assets):
            alloc_usd = initial_capital * target_weights[i]
            p0 = prices[0, i]
            shares = alloc_usd / p0
            
            # Compute Frictions
            spread_c = alloc_usd * self.half_spread
            comm_c = alloc_usd * self.commission_rate + self.fixed_ticket_fee
            impact_c = alloc_usd * (self.market_impact_lambda * np.sqrt(alloc_usd / max(1000.0, adv[i])))
            total_f = spread_c + comm_c + impact_c
            
            current_holdings[i] = shares
            cash -= (alloc_usd + total_f)
            
            trades.append(BacktestTradeRecord(
                step_index=0,
                date_label="T0_INIT",
                asset=asset_names[i],
                action="BUY",
                shares=float(shares),
                price=float(p0),
                notional=float(alloc_usd),
                spread_cost=float(spread_c),
                market_impact_cost=float(impact_c),
                commission_cost=float(comm_c),
                total_friction=float(total_f)
            ))
            
        port_val_0 = float(cash + np.sum(current_holdings * prices[0, :]))
        equity_curve.append(port_val_0)
        
        # Walk Forward from Step 1 to T-1
        total_turnover = float(initial_capital)
        total_friction = sum(t.total_friction for t in trades)
        
        for t in range(1, t_steps):
            current_prices = prices[t, :]
            asset_values = current_holdings * current_prices
            total_port_val = float(cash + np.sum(asset_values))
            
            # Check Rebalancing Trigger (Calendar or Corridor Drift)
            is_calendar_step = (t % rebalance_frequency_steps == 0)
            current_w = asset_values / max(1.0, total_port_val)
            weight_drifts = np.abs(current_w - target_weights)
            is_corridor_breached = np.any(weight_drifts > rebalance_corridor_pct)
            
            if is_calendar_step or is_corridor_breached:
                # Rebalance back to target weights
                for i in range(n_assets):
                    target_usd = total_port_val * target_weights[i]
                    drift_usd = target_usd - asset_values[i]
                    
                    if abs(drift_usd) > 500.0: # Ignore immaterial sub-$500 trades
                        p_now = current_prices[i]
                        d_shares = drift_usd / p_now
                        notional = abs(drift_usd)
                        
                        spread_c = notional * self.half_spread
                        comm_c = notional * self.commission_rate + self.fixed_ticket_fee
                        impact_c = notional * (self.market_impact_lambda * np.sqrt(notional / max(1000.0, adv[i])))
                        total_f = spread_c + comm_c + impact_c
                        
                        current_holdings[i] += d_shares
                        cash -= (drift_usd + total_f)
                        total_turnover += notional
                        total_friction += total_f
                        
                        trades.append(BacktestTradeRecord(
                            step_index=t,
                            date_label=f"T{t}",
                            asset=asset_names[i],
                            action="BUY" if d_shares > 0 else "SELL",
                            shares=float(abs(d_shares)),
                            price=float(p_now),
                            notional=float(notional),
                            spread_cost=float(spread_c),
                            market_impact_cost=float(impact_c),
                            commission_cost=float(comm_c),
                            total_friction=float(total_f)
                        ))
                        
            # Record Point-in-Time Equity
            port_val_t = float(cash + np.sum(current_holdings * current_prices))
            equity_curve.append(port_val_t)
            
        # ==================== ADVANCED METRICS COMPUTATION ====================
        eq_arr = np.array(equity_curve)
        daily_returns = (eq_arr[1:] - eq_arr[:-1]) / eq_arr[:-1]
        
        # 1. Cumulative Return & CAGR (Assumes 252 trading days/yr)
        years = max(0.01, (t_steps - 1) / 252.0)
        total_return_pct = ((eq_arr[-1] - initial_capital) / initial_capital) * 100.0
        cagr_pct = (((eq_arr[-1] / initial_capital) ** (1.0 / years)) - 1.0) * 100.0
        
        # 2. Volatility & Downside Volatility
        ann_vol = float(np.std(daily_returns) * np.sqrt(252)) * 100.0
        downside_diffs = np.minimum(0.0, daily_returns - (self.risk_free_rate / 252.0))
        downside_dev = float(np.sqrt(np.mean(downside_diffs ** 2)) * np.sqrt(252)) * 100.0
        
        # 3. Sharpe, Sortino, Calmar
        mean_excess_ann = (float(np.mean(daily_returns) * 252) - self.risk_free_rate) * 100.0
        sharpe = (mean_excess_ann / ann_vol) if ann_vol > 0 else 0.0
        sortino = (mean_excess_ann / downside_dev) if downside_dev > 0 else 0.0
        
        # 4. Drawdown Series & Max Drawdown
        peak_arr = np.maximum.accumulate(eq_arr)
        drawdowns = (eq_arr - peak_arr) / peak_arr
        max_dd_pct = float(np.min(drawdowns)) * 100.0
        
        # Longest underwater duration
        underwater = (drawdowns < 0)
        max_duration = 0
        curr_duration = 0
        for is_uw in underwater:
            if is_uw:
                curr_duration += 1
                max_duration = max(max_duration, curr_duration)
            else:
                curr_duration = 0
                
        calmar = (cagr_pct / abs(max_dd_pct)) if abs(max_dd_pct) > 0 else 0.0
        
        # 5. Omega Ratio (Threshold = Rf / 252)
        rf_daily = self.risk_free_rate / 252.0
        gains = np.maximum(0.0, daily_returns - rf_daily)
        losses = np.maximum(0.0, rf_daily - daily_returns)
        sum_losses = np.sum(losses)
        omega = float(np.sum(gains) / sum_losses) if sum_losses > 0 else 1.0
        
        friction_bps = (total_friction / max(1.0, total_turnover)) * 10000.0
        
        return BacktestReport(
            strategy_name=strategy_name,
            initial_capital=initial_capital,
            ending_capital=float(eq_arr[-1]),
            total_return_pct=round(total_return_pct, 2),
            cagr_pct=round(cagr_pct, 2),
            annualized_volatility_pct=round(ann_vol, 2),
            downside_deviation_pct=round(downside_dev, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            calmar_ratio=round(calmar, 2),
            omega_ratio=round(omega, 2),
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_duration_steps=int(max_duration),
            total_turnover_usd=round(total_turnover, 2),
            total_friction_drag_usd=round(total_friction, 2),
            total_friction_drag_bps=round(friction_bps, 1),
            equity_curve=list(np.round(eq_arr, 2)),
            drawdown_series=list(np.round(drawdowns * 100.0, 2)),
            trade_records=trades
        )

if __name__ == "__main__":
    print("Testing Walk-Forward Backtester & Execution Slippage Simulator...")
    bt = WalkForwardBacktester()
    
    # Generate 252 days of geometric brownian motion for 3 assets
    np.random.seed(42)
    t_days = 252
    mu = np.array([0.10, 0.07, 0.04]) / 252.0
    sigma = np.array([0.18, 0.14, 0.05]) / np.sqrt(252.0)
    
    returns = np.random.normal(mu, sigma, size=(t_days, 3))
    prices = 100.0 * np.exp(np.cumsum(returns, axis=0))
    
    rep = bt.run_backtest(
        strategy_name="Institutional 60/30/10 Core Mandate",
        asset_names=["US Equities", "Intl Equities", "US Treasuries"],
        price_matrix=prices,
        target_weights=np.array([0.60, 0.30, 0.10]),
        initial_capital=10000000.0,
        rebalance_corridor_pct=0.03
    )
    print(f"✓ Backtest Result: {rep.strategy_name}")
    print(f"  • Ending Capital: ${rep.ending_capital:,.2f} ({rep.total_return_pct:+.2f}%)")
    print(f"  • Sharpe: {rep.sharpe_ratio:.2f} | Sortino: {rep.sortino_ratio:.2f} | Max Drawdown: {rep.max_drawdown_pct:.2f}%")
    print(f"  • Turnover: ${rep.total_turnover_usd:,.2f} | Total Friction: ${rep.total_friction_drag_usd:,.2f} ({rep.total_friction_drag_bps:.1f} bps)")
