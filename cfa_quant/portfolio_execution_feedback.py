"""
CFA Level III Portfolio Execution & Feedback Engine
Implements:
1. Black-Litterman Bayesian Portfolio Optimization
2. Brinson-Fachler Multi-Sector Performance Attribution
3. Dynamic Optimal Rebalancing Corridors Engine
"""

from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd

class PortfolioExecutionFeedbackEngine:
    def __init__(self):
        pass

    def run_black_litterman_optimization(
        self,
        asset_names: List[str],
        market_caps: np.ndarray,
        covariance_matrix: np.ndarray,
        risk_aversion: float = 2.5,
        risk_free_rate: float = 0.045,
        views_pick_matrix: Optional[np.ndarray] = None,
        views_expected_returns: Optional[np.ndarray] = None,
        views_uncertainties: Optional[np.ndarray] = None,
        tau: float = 0.05
    ) -> Dict[str, Any]:
        """
        CFA Level III Black-Litterman Model:
        1. Implied Equilibrium Returns: Pi = lambda * Sigma * w_mkt
        2. Posterior Combined Expected Returns: E(R) = [ (tau*Sigma)^-1 + P^T Omega^-1 P ]^-1 [ (tau*Sigma)^-1 Pi + P^T Omega^-1 Q ]
        3. Optimal Weights: w* = (lambda * Sigma)^-1 E(R)
        """
        w_mkt = market_caps / np.sum(market_caps)
        sigma = np.asarray(covariance_matrix)
        
        # 1. Reverse optimization: Implied Equilibrium Returns
        pi = risk_aversion * np.dot(sigma, w_mkt)
        
        if views_pick_matrix is None or views_expected_returns is None:
            # Neutral benchmark allocation
            bl_returns = pi + risk_free_rate
            opt_weights = w_mkt
        else:
            P = np.asarray(views_pick_matrix)
            Q = np.asarray(views_expected_returns)
            
            if views_uncertainties is None:
                # Default He-Litterman diagonal Omega = diag(P * (tau * Sigma) * P^T)
                omega = np.diag(np.diag(np.dot(np.dot(P, tau * sigma), P.T)))
            else:
                omega = np.asarray(views_uncertainties)
                
            # Bayesian update equations
            tau_sigma_inv = np.linalg.inv(tau * sigma)
            omega_inv = np.linalg.inv(omega)
            
            middle_term = np.linalg.inv(tau_sigma_inv + np.dot(np.dot(P.T, omega_inv), P))
            bl_excess_returns = np.dot(middle_term, np.dot(tau_sigma_inv, pi) + np.dot(np.dot(P.T, omega_inv), Q))
            bl_returns = bl_excess_returns + risk_free_rate
            
            # Unconstrained optimal active weights
            opt_weights = np.dot(np.linalg.inv(risk_aversion * sigma), bl_excess_returns)
            opt_weights = opt_weights / np.sum(opt_weights)  # Normalize to 100%
            
        return {
            "asset_names": asset_names,
            "market_cap_weights": [round(float(w), 4) for w in w_mkt],
            "implied_equilibrium_returns_pct": [round(float(r + risk_free_rate) * 100, 2) for r in pi],
            "black_litterman_posterior_returns_pct": [round(float(r) * 100, 2) for r in bl_returns],
            "optimal_portfolio_weights_pct": [round(float(w) * 100, 2) for w in opt_weights]
        }

    def compute_brinson_fachler_attribution(
        self,
        sectors: List[str],
        portfolio_weights: np.ndarray,
        benchmark_weights: np.ndarray,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray
    ) -> Dict[str, Any]:
        """
        CFA Level III Brinson-Fachler Performance Attribution:
        Allocation Effect: A_i = (w_i - W_i) * (B_i - B)
        Selection Effect:  S_i = W_i * (R_i - B_i)
        Interaction Effect:I_i = (w_i - W_i) * (R_i - B_i)
        Total Active Return: R_p - R_b = sum(A_i + S_i + I_i)
        """
        w = np.asarray(portfolio_weights)
        W = np.asarray(benchmark_weights)
        R = np.asarray(portfolio_returns)
        B = np.asarray(benchmark_returns)
        
        total_benchmark_return = np.sum(W * B)
        total_portfolio_return = np.sum(w * R)
        total_active_return = total_portfolio_return - total_benchmark_return
        
        allocation_effects = (w - W) * (B - total_benchmark_return)
        selection_effects = W * (R - B)
        interaction_effects = (w - W) * (R - B)
        
        breakdown = []
        for i in range(len(sectors)):
            breakdown.append({
                "sector": sectors[i],
                "portfolio_weight_pct": round(float(w[i]) * 100, 2),
                "benchmark_weight_pct": round(float(W[i]) * 100, 2),
                "portfolio_return_pct": round(float(R[i]) * 100, 2),
                "benchmark_return_pct": round(float(B[i]) * 100, 2),
                "allocation_effect_bps": round(float(allocation_effects[i]) * 10000, 1),
                "selection_effect_bps": round(float(selection_effects[i]) * 10000, 1),
                "interaction_effect_bps": round(float(interaction_effects[i]) * 10000, 1),
                "total_sector_active_bps": round(float(allocation_effects[i] + selection_effects[i] + interaction_effects[i]) * 10000, 1)
            })
            
        return {
            "total_portfolio_return_pct": round(total_portfolio_return * 100, 2),
            "total_benchmark_return_pct": round(total_benchmark_return * 100, 2),
            "total_active_return_bps": round(total_active_return * 10000, 1),
            "total_allocation_effect_bps": round(float(np.sum(allocation_effects)) * 10000, 1),
            "total_selection_effect_bps": round(float(np.sum(selection_effects)) * 10000, 1),
            "total_interaction_effect_bps": round(float(np.sum(interaction_effects)) * 10000, 1),
            "sector_breakdown": breakdown
        }

    def compute_dynamic_rebalancing_corridors(
        self,
        target_weight: float,
        asset_volatility: float,
        transaction_cost_bps: float = 15.0,
        risk_tolerance_factor: float = 1.0,  # 0.8 for conservative, 1.2 for aggressive
        correlation_with_portfolio: float = 0.70
    ) -> Dict[str, Any]:
        """
        CFA Level III Optimal Corridor Width Rule:
        Corridor Width proportional to: (TxCost / Volatility) * Risk_Tolerance * (1 + Correlation)
        """
        base_width = 0.05 * target_weight  # Standard 5% relative band
        
        # Volatility penalty (higher vol -> narrower band to control risk)
        vol_adj = 0.20 / max(asset_volatility, 0.05)
        
        # Cost incentive (higher tx costs -> wider band to avoid churn)
        cost_adj = 1.0 + (transaction_cost_bps / 50.0)
        
        # Correlation incentive (higher correlation -> wider band because asset moves with portfolio)
        corr_adj = 0.75 + (0.5 * correlation_with_portfolio)
        
        optimal_half_width = base_width * vol_adj * cost_adj * corr_adj * risk_tolerance_factor
        # Floor and ceiling boundaries
        optimal_half_width = np.clip(optimal_half_width, 0.01, 0.12)
        
        lower_bound = max(0.0, target_weight - optimal_half_width)
        upper_bound = min(1.0, target_weight + optimal_half_width)
        
        return {
            "target_weight_pct": round(target_weight * 100, 2),
            "optimal_half_width_pct": round(optimal_half_width * 100, 2),
            "lower_rebalancing_corridor_pct": round(lower_bound * 100, 2),
            "upper_rebalancing_corridor_pct": round(upper_bound * 100, 2),
            "rebalancing_trigger_rule": f"Rebalance when weight breaches [{lower_bound*100:.1f}%, {upper_bound*100:.1f}%]"
        }

if __name__ == "__main__":
    engine = PortfolioExecutionFeedbackEngine()
    print("=" * 75)
    print("🏛️ CFA LEVEL III PORTFOLIO EXECUTION & FEEDBACK ENGINE")
    print("=" * 75)
    
    # Test Brinson-Fachler Attribution
    sectors = ["Information Technology", "Health Care", "Financials", "Consumer Discretionary", "Energy"]
    w_port = np.array([0.35, 0.15, 0.20, 0.15, 0.15])
    w_bmk = np.array([0.28, 0.14, 0.18, 0.12, 0.28])
    r_port = np.array([0.22, 0.08, 0.12, 0.15, -0.05])
    r_bmk = np.array([0.18, 0.07, 0.10, 0.11, -0.08])
    
    attr = engine.compute_brinson_fachler_attribution(sectors, w_port, w_bmk, r_port, r_bmk)
    print(f"Portfolio Return: {attr['total_portfolio_return_pct']}% | Benchmark Return: {attr['total_benchmark_return_pct']}%")
    print(f"Total Active Return (Alpha): {attr['total_active_return_bps']:+0.1f} bps")
    print(f"  • Allocation Effect: {attr['total_allocation_effect_bps']:+0.1f} bps")
    print(f"  • Selection Effect:  {attr['total_selection_effect_bps']:+0.1f} bps")
    print(f"  • Interaction Effect:{attr['total_interaction_effect_bps']:+0.1f} bps")
    print("=" * 75)
