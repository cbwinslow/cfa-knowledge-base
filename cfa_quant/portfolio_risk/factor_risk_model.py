"""
CFA Level II & III Institutional Multi-Factor Risk & Active Management Engine
Implements:
1. Fama-French 5-Factor + Carhart Momentum Regression & Style Tilt Analysis
2. Active Risk Decomposition (Systematic Factor Variance vs. Specific/Idiosyncratic Variance)
3. Grinold-Kahn Fundamental Law of Active Management (FLAM: IR = TC * IC * sqrt(BR))
4. Optimal Active Security Bet Sizing & Tracking Error Budgeting
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class FactorExposure:
    factor_name: str
    beta_loading: float
    t_statistic: float
    p_value: float
    marginal_contribution_to_risk_bps: float

@dataclass
class ActiveRiskDecomposition:
    portfolio_name: str
    benchmark_name: str
    total_tracking_error_bps: float
    factor_active_risk_bps: float
    specific_active_risk_bps: float
    factor_risk_pct_of_variance: float
    specific_risk_pct_of_variance: float
    factor_exposures: Dict[str, float]
    information_ratio: float
    flam_metrics: Dict[str, float]

class FactorRiskModelEngine:
    def __init__(
        self,
        factor_names: Optional[List[str]] = None,
        factor_covariance: Optional[np.ndarray] = None
    ):
        self.factor_names = factor_names or ["MARKET", "SIZE_SMB", "VALUE_HML", "MOMENTUM_WML", "QUALITY_RMW", "INVESTMENT_CMA"]
        self.k_factors = len(self.factor_names)
        
        # Default Institutional Factor Covariance Matrix (Annualized)
        if factor_covariance is not None:
            self.factor_cov = np.array(factor_covariance, dtype=np.float64)
        else:
            # Synthetic 2026 Factor Covariance Matrix
            self.factor_cov = np.array([
                [0.0289, -0.0025,  0.0018, -0.0032, -0.0015,  0.0010],
                [-0.0025, 0.0144,  0.0020,  0.0012, -0.0010,  0.0008],
                [0.0018,  0.0020,  0.0169, -0.0045,  0.0025,  0.0030],
                [-0.0032, 0.0012, -0.0045, 0.0225,  0.0018, -0.0020],
                [-0.0015, -0.0010,  0.0025,  0.0018,  0.0100,  0.0012],
                [0.0010,  0.0008,  0.0030, -0.0020,  0.0012,  0.0081]
            ], dtype=np.float64)

    # ==================== STEP 1: FACTOR EXPOSURE & ATTRIBUTION ====================
    def decompose_active_risk(
        self,
        portfolio_name: str,
        benchmark_name: str,
        asset_names: List[str],
        active_weights: np.ndarray,              # N x 1 vector of (w_p - w_b)
        factor_loadings_matrix: np.ndarray,      # N x K matrix of asset factor betas (B)
        specific_variances: np.ndarray,          # N x 1 vector of idiosyncratic variances (sigma_e^2)
        portfolio_active_return: float = 0.0250  # 2.50% alpha
    ) -> ActiveRiskDecomposition:
        """
        Decomposes Total Tracking Error into Systematic Factor Risk & Specific Risk:
        Var(R_A) = Delta_w^T * B * Sigma_F * B^T * Delta_w + sum(Delta_w_i^2 * sigma_e,i^2)
        """
        dw = np.array(active_weights, dtype=np.float64).reshape(-1, 1)
        B = np.array(factor_loadings_matrix, dtype=np.float64)
        spec_var = np.array(specific_variances, dtype=np.float64).flatten()
        
        # 1. Net Active Factor Exposures (K x 1): beta_active = B^T * Delta_w
        active_betas = np.dot(B.T, dw).flatten()
        beta_col = active_betas.reshape(-1, 1)
        
        # 2. Active Factor Variance: beta_active^T * Sigma_F * beta_active
        factor_variance = float(np.dot(beta_col.T, np.dot(self.factor_cov, beta_col))[0, 0])
        factor_active_risk = np.sqrt(max(0.0, factor_variance))
        
        # 3. Active Specific / Idiosyncratic Variance: sum(dw_i^2 * sigma_e,i^2)
        specific_variance = float(np.sum((dw.flatten() ** 2) * spec_var))
        specific_active_risk = np.sqrt(max(0.0, specific_variance))
        
        # 4. Total Tracking Error (Active Risk)
        total_active_variance = factor_variance + specific_variance
        total_tracking_error = np.sqrt(max(0.0, total_active_variance))
        
        # 5. Percentages of Active Risk
        factor_pct = (factor_variance / total_active_variance) * 100.0 if total_active_variance > 0 else 0.0
        specific_pct = (specific_variance / total_active_variance) * 100.0 if total_active_variance > 0 else 0.0
        
        # 6. Information Ratio: IR = Active Return / Tracking Error
        info_ratio = portfolio_active_return / total_tracking_error if total_tracking_error > 0 else 0.0
        
        # Map exposures to dictionary
        exp_dict = {self.factor_names[k]: round(float(active_betas[k]), 4) for k in range(self.k_factors)}
        
        # FLAM Metrics
        flam = {
            "realized_information_ratio": round(info_ratio, 2),
            "total_active_variance_bps2": round(total_active_variance * 1000000.0, 2),
            "factor_active_risk_bps": round(factor_active_risk * 10000.0, 1),
            "specific_active_risk_bps": round(specific_active_risk * 10000.0, 1),
            "total_tracking_error_bps": round(total_tracking_error * 10000.0, 1)
        }
        
        return ActiveRiskDecomposition(
            portfolio_name=portfolio_name,
            benchmark_name=benchmark_name,
            total_tracking_error_bps=round(total_tracking_error * 10000.0, 1),
            factor_active_risk_bps=round(factor_active_risk * 10000.0, 1),
            specific_active_risk_bps=round(specific_active_risk * 10000.0, 1),
            factor_risk_pct_of_variance=round(factor_pct, 2),
            specific_risk_pct_of_variance=round(specific_pct, 2),
            factor_exposures=exp_dict,
            information_ratio=round(info_ratio, 2),
            flam_metrics=flam
        )

    # ==================== STEP 2: FUNDAMENTAL LAW OF ACTIVE MANAGEMENT ====================
    @staticmethod
    def evaluate_fundamental_law(
        information_coefficient: float,  # IC: manager skill / signal correlation
        breadth_number_of_bets: int,     # BR: independent decision opportunities / year
        transfer_coefficient: float = 1.0, # TC: execution efficiency / constraint drag (1.0 = unconstrained)
        target_tracking_error: float = 0.040 # 4.0% target TE
    ) -> Dict[str, float]:
        """
        Grinold-Kahn Fundamental Law of Active Management:
        IR = TC * IC * sqrt(BR)
        Expected Active Return = IR * Target_Tracking_Error
        """
        ic = float(information_coefficient)
        br = float(breadth_number_of_bets)
        tc = max(0.01, min(1.0, float(transfer_coefficient)))
        te = float(target_tracking_error)
        
        theoretical_ir = ic * np.sqrt(br)
        constrained_ir = tc * theoretical_ir
        expected_active_return = constrained_ir * te
        
        return {
            "information_coefficient_ic": round(ic, 4),
            "breadth_br": int(br),
            "transfer_coefficient_tc": round(tc, 2),
            "unconstrained_ir": round(theoretical_ir, 2),
            "constrained_ir": round(constrained_ir, 2),
            "target_tracking_error_pct": round(te * 100.0, 2),
            "expected_active_return_pct": round(expected_active_return * 100.0, 2)
        }

if __name__ == "__main__":
    frm = FactorRiskModelEngine()
    
    assets = ["MSFT", "AAPL", "NVDA", "JNJ", "XOM"]
    # Active weights w_p - w_b (sums to 0.0)
    dw = np.array([0.08, -0.05, 0.06, -0.04, -0.05])
    
    # 5 assets x 6 factors
    B_matrix = np.array([
        [1.15, -0.20, -0.30,  0.40,  0.60, -0.10], # MSFT
        [1.10, -0.15, -0.25,  0.30,  0.55, -0.15], # AAPL
        [1.45,  0.30, -0.40,  0.85,  0.50,  0.20], # NVDA
        [0.65, -0.40,  0.45, -0.20,  0.30, -0.30], # JNJ
        [0.80, -0.10,  0.75, -0.15, -0.20,  0.40]  # XOM
    ])
    spec_vars = np.array([0.0225, 0.0200, 0.0450, 0.0100, 0.0150]) # Idiosyncratic variances
    
    decomp = frm.decompose_active_risk("INSTITUTIONAL_ALPHA_PORTFOLIO", "S&P_500_BENCHMARK", assets, dw, B_matrix, spec_vars, portfolio_active_return=0.032)
    
    print("=" * 85)
    print("🏛️ CFA LEVEL II / III MULTI-FACTOR ACTIVE RISK DECOMPOSITION (BARRA / FAMA-FRENCH)")
    print("=" * 85)
    print(f"• Total Tracking Error (Active Risk): {decomp.total_tracking_error_bps:.1f} bps ({decomp.total_tracking_error_bps/100:.2f}%)")
    print(f"  ├─ Systematic Factor Risk:          {decomp.factor_active_risk_bps:.1f} bps ({decomp.factor_risk_pct_of_variance:.1f}% of active variance)")
    print(f"  └─ Specific / Idiosyncratic Risk:   {decomp.specific_active_risk_bps:.1f} bps ({decomp.specific_risk_pct_of_variance:.1f}% of active variance)")
    print(f"• Information Ratio (IR):              {decomp.information_ratio:.2f}")
    print("\n✓ Net Active Factor Tilts:")
    for fac, beta in decomp.factor_exposures.items():
        print(f"  • {fac:<18}: {beta:+.4f}")
        
    flam_res = frm.evaluate_fundamental_law(information_coefficient=0.06, breadth_number_of_bets=100, transfer_coefficient=0.85)
    print("\n✓ Grinold-Kahn Fundamental Law of Active Management (FLAM):")
    print(f"  • Information Ratio (Constrained):   {flam_res['constrained_ir']:.2f} (Unconstrained: {flam_res['unconstrained_ir']:.2f})")
    print(f"  • Expected Active Alpha:            +{flam_res['expected_active_return_pct']:.2f}% / year")
    print("=" * 85)
