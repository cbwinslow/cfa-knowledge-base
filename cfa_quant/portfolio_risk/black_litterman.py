"""
CFA Level III Institutional Black-Litterman Asset Allocation Engine
Implements:
1. Implied Equilibrium Returns (Reverse Optimization: Pi = lambda * Sigma * w_mkt)
2. Subjective Investor Views Pick Matrix (P), View Vector (Q), and Confidence Scaling
3. He-Litterman & Idzorek Uncertainty Covariance (Omega = tau * P * Sigma * P^T)
4. Posterior Master Distribution: Expected Returns (mu_bl) & Covariance (Sigma_bl)
5. Optimal Active Tilt Weights (Unconstrained and Long-Only Constrained Optimization)
"""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from scipy.optimize import minimize

class BlackLittermanEngine:
    def __init__(
        self,
        asset_names: List[str],
        covariance_matrix: np.ndarray,
        market_weights: np.ndarray,
        risk_aversion: float = 2.5,
        tau: float = 0.05,
        risk_free_rate: float = 0.0435
    ):
        """
        :param asset_names: List of N asset names/tickers
        :param covariance_matrix: N x N historical/forecast covariance matrix (Sigma)
        :param market_weights: N x 1 benchmark market capitalization weights (sums to 1.0)
        :param risk_aversion: Market risk aversion parameter lambda = (E(r_m) - r_f) / sigma_m^2
        :param tau: Weight-on-views scaling scalar (typically 0.025 to 0.05)
        :param risk_free_rate: Benchmark risk-free rate (SOFR / 10Y Treasury, Year 2026)
        """
        self.asset_names = asset_names
        self.n_assets = len(asset_names)
        self.sigma = np.array(covariance_matrix, dtype=np.float64)
        self.w_mkt = np.array(market_weights, dtype=np.float64)
        self.risk_aversion = float(risk_aversion)
        self.tau = float(tau)
        self.rf = float(risk_free_rate)
        
        # Normalize market weights
        if abs(np.sum(self.w_mkt) - 1.0) > 1e-4:
            self.w_mkt = self.w_mkt / np.sum(self.w_mkt)
            
        # 1. Compute Implied Equilibrium Benchmark Returns (Pi)
        self.pi = self.compute_implied_equilibrium_returns()

    # ==================== STEP 1: REVERSE OPTIMIZATION ====================
    def compute_implied_equilibrium_returns(self) -> np.ndarray:
        """
        Computes the neutral market equilibrium return vector:
        Pi = lambda * Sigma * w_mkt
        """
        return self.risk_aversion * np.dot(self.sigma, self.w_mkt)

    # ==================== STEP 2 & 3: VIEWS & POSTERIOR BLENDING ====================
    def blend_views(
        self,
        p_matrix: np.ndarray,
        q_vector: np.ndarray,
        confidences: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Blends subjective views with market equilibrium to produce Black-Litterman posterior.
        
        :param p_matrix: K x N matrix where K is number of views and N is number of assets
        :param q_vector: K x 1 vector of view expected returns
        :param confidences: Optional list of K confidence values in [0.0, 1.0]
        """
        P = np.array(p_matrix, dtype=np.float64)
        Q = np.array(q_vector, dtype=np.float64).reshape(-1, 1)
        k_views = P.shape[0]
        
        if P.shape[1] != self.n_assets:
            raise ValueError(f"P matrix columns ({P.shape[1]}) must match number of assets ({self.n_assets})")

        # Prior covariance on equilibrium returns: tau * Sigma
        tau_sigma = self.tau * self.sigma
        inv_tau_sigma = np.linalg.inv(tau_sigma)

        # Compute Omega (Diagonal view uncertainty covariance matrix)
        omega = np.zeros((k_views, k_views), dtype=np.float64)
        for k in range(k_views):
            p_k = P[k:k+1, :]
            # He-Litterman baseline variance for view k: p_k * (tau * Sigma) * p_k^T
            var_k = float(np.dot(p_k, np.dot(tau_sigma, p_k.T))[0, 0])
            
            if confidences is not None and k < len(confidences):
                conf = max(0.01, min(0.99, float(confidences[k])))
                # Scale uncertainty inversely with confidence
                omega[k, k] = var_k * ((1.0 - conf) / conf)
            else:
                omega[k, k] = var_k

        inv_omega = np.linalg.inv(omega)

        # Black-Litterman Master Formula:
        # M_inverse = [(tau * Sigma)^-1 + P^T * Omega^-1 * P]
        m_inv = inv_tau_sigma + np.dot(P.T, np.dot(inv_omega, P))
        m_matrix = np.linalg.inv(m_inv)

        # Posterior Expected Returns: mu_bl = M * [(tau * Sigma)^-1 * Pi + P^T * Omega^-1 * Q]
        pi_col = self.pi.reshape(-1, 1)
        term1 = np.dot(inv_tau_sigma, pi_col)
        term2 = np.dot(P.T, np.dot(inv_omega, Q))
        mu_bl = np.dot(m_matrix, (term1 + term2)).flatten()

        # Posterior Covariance Matrix: Sigma_bl = Sigma + M
        sigma_bl = self.sigma + m_matrix

        # Unconstrained Analytical Optimal Weights: w_bl = (1 / lambda) * Sigma_bl^-1 * mu_bl
        inv_sigma_bl = np.linalg.inv(sigma_bl)
        w_unconstrained = (1.0 / self.risk_aversion) * np.dot(inv_sigma_bl, mu_bl)
        if np.sum(w_unconstrained) != 0:
            w_unconstrained_normalized = w_unconstrained / np.sum(w_unconstrained)
        else:
            w_unconstrained_normalized = w_unconstrained

        # Long-Only Constrained Optimal Weights (w_i >= 0, sum(w) = 1.0)
        w_constrained = self._optimize_long_only_weights(mu_bl, sigma_bl)

        # Active Weight Tilts (w_bl - w_mkt)
        active_tilts = w_constrained - self.w_mkt

        return {
            "implied_equilibrium_returns": self.pi.tolist(),
            "posterior_expected_returns": mu_bl.tolist(),
            "posterior_covariance_matrix": sigma_bl.tolist(),
            "market_benchmark_weights": self.w_mkt.tolist(),
            "unconstrained_weights": w_unconstrained_normalized.tolist(),
            "optimal_constrained_weights": w_constrained.tolist(),
            "active_tilts": active_tilts.tolist(),
            "views_summary": [
                {
                    "view_index": i + 1,
                    "expected_return": float(Q[i, 0]),
                    "uncertainty_variance": float(omega[i, i]),
                    "confidence_score": float(confidences[i]) if confidences else 0.50
                }
                for i in range(k_views)
            ]
        }

    # ==================== STEP 4: LONG-ONLY CONSTRAINED SOLVER ====================
    def _optimize_long_only_weights(self, mu: np.ndarray, sigma: np.ndarray) -> np.ndarray:
        """
        Solves the Markowitz Quadratic Utility Maximization subject to long-only constraints:
        max w^T * mu - 0.5 * lambda * w^T * Sigma * w
        subject to sum(w) = 1, w_i >= 0
        """
        def objective(w):
            port_ret = np.dot(w, mu)
            port_var = np.dot(w, np.dot(sigma, w))
            # Negative utility for minimization
            return -(port_ret - 0.5 * self.risk_aversion * port_var)

        init_w = np.ones(self.n_assets) / self.n_assets
        bounds = [(0.0, 1.0) for _ in range(self.n_assets)]
        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})

        res = minimize(objective, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
        if res.success:
            return res.x
        return init_w

if __name__ == "__main__":
    assets = ["US_EQUITIES", "GLOBAL_EQUITIES", "US_TREASURIES", "EM_BONDS"]
    cov = np.array([
        [0.040, 0.025, 0.002, 0.010],
        [0.025, 0.050, 0.001, 0.015],
        [0.002, 0.001, 0.008, 0.003],
        [0.010, 0.015, 0.003, 0.025]
    ])
    w_m = np.array([0.45, 0.25, 0.20, 0.10])
    
    bl = BlackLittermanEngine(assets, cov, w_m, risk_aversion=2.5, tau=0.05)
    
    print("=" * 80)
    print("🏛️ CFA LEVEL III BLACK-LITTERMAN ASSET ALLOCATION ENGINE")
    print("=" * 80)
    print("• Market Benchmark Weights:", dict(zip(assets, [f"{w*100:.1f}%" for w in w_m])))
    print("• Implied Equilibrium Returns (Pi):", dict(zip(assets, [f"{r*100:.2f}%" for r in bl.pi])))
    
    # View 1: US Equities will outperform Global Equities by 2.0%
    # View 2: US Treasuries will return 5.5% absolute
    P = np.array([
        [1.0, -1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0]
    ])
    Q = np.array([0.020, 0.055])
    conf = [0.75, 0.90]
    
    res = bl.blend_views(P, Q, conf)
    print("\n✓ Posterior Expected Returns (mu_bl):", dict(zip(assets, [f"{r*100:.2f}%" for r in res["posterior_expected_returns"]])))
    print("✓ Optimal Constrained Allocation (w*):", dict(zip(assets, [f"{w*100:.1f}%" for w in res["optimal_constrained_weights"]])))
    print("✓ Active Tilts (w* - w_mkt):", dict(zip(assets, [f"{t*100:+.2f}%" for t in res["active_tilts"]])))
    print("=" * 80)
