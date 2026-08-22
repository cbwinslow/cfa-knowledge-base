"""
Stochastic Asset Pricing & Financial Statement Simulation Engine.
Implements:
1. Statsmodels Markov Autoregression (Hamilton Regime Switching)
2. Merton Jump Diffusion (Compound Poisson Jump Process)
3. Stochastic Pro-Forma Financial Statement Modeling
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from statsmodels.tsa.regime_switching.markov_autoregression import (
    MarkovAutoregression,
    MarkovAutoregressionResultsWrapper,
)

@dataclass(frozen=True)
class MarkovRegimeParameters:
    k_regimes: int
    transition_matrix: np.ndarray
    regime_means: np.ndarray
    regime_variances: np.ndarray
    ar_coefficients: np.ndarray
    initial_probabilities: np.ndarray

@dataclass(frozen=True)
class MJDParameters:
    drift: float              # Total expected annual drift (mu)
    volatility: float         # Continuous annual volatility (sigma)
    jump_intensity: float     # Poisson jump rate per year (lambda)
    jump_mean: float          # Mean log jump size (mu_J)
    jump_std: float           # Std dev of log jump size (sigma_J)

    @property
    def jump_compensator(self) -> float:
        return float(np.exp(self.jump_mean + 0.5 * (self.jump_std ** 2)) - 1.0)

@dataclass(frozen=True)
class FinancialStatementAssumptions:
    initial_revenue: float
    tax_rate: float = 0.21
    depreciation_rate_of_ppe: float = 0.10
    capex_to_revenue: float = 0.05
    nwc_to_revenue: float = 0.15
    interest_rate: float = 0.05
    initial_debt: float = 0.0
    initial_cash: float = 50.0
    initial_ppe: float = 200.0

@dataclass
class SimulationResult:
    time_grid: np.ndarray
    paths: np.ndarray  # Shape: (num_simulations, num_steps + 1)
    regimes: Optional[np.ndarray] = None

    @property
    def mean_path(self) -> np.ndarray:
        return np.mean(self.paths, axis=0)

    @property
    def median_path(self) -> np.ndarray:
        return np.median(self.paths, axis=0)

    def quantile(self, q: float) -> np.ndarray:
        return np.quantile(self.paths, q=q, axis=0)

    def var(self, alpha: float = 0.05) -> float:
        terminal_returns = (self.paths[:, -1] - self.paths[:, 0]) / self.paths[:, 0]
        return float(-np.quantile(terminal_returns, q=alpha))

    def cvar(self, alpha: float = 0.05) -> float:
        terminal_returns = (self.paths[:, -1] - self.paths[:, 0]) / self.paths[:, 0]
        var_threshold = np.quantile(terminal_returns, q=alpha)
        tail_losses = terminal_returns[terminal_returns <= var_threshold]
        return float(-np.mean(tail_losses))

class MarkovRegimeEngine:
    def __init__(self, k_regimes: int = 2, order: int = 1, switching_ar: bool = True, switching_variance: bool = True):
        self.k_regimes = k_regimes
        self.order = order
        self.switching_ar = switching_ar
        self.switching_variance = switching_variance
        self.fitted_model: Optional[MarkovAutoregressionResultsWrapper] = None
        self.params_: Optional[MarkovRegimeParameters] = None

    def fit(self, endog: Union[pd.Series, np.ndarray], search_reps: int = 20) -> MarkovRegimeEngine:
        endog_clean = np.asarray(endog, dtype=float)
        model = MarkovAutoregression(
            endog=endog_clean,
            k_regimes=self.k_regimes,
            order=self.order,
            trend="c",
            switching_ar=self.switching_ar,
            switching_variance=self.switching_variance,
        )
        self.fitted_model = model.fit(search_reps=search_reps, disp=False)
        self.params_ = self._extract_parameters(self.fitted_model)
        return self

    def _extract_parameters(self, results: MarkovAutoregressionResultsWrapper) -> MarkovRegimeParameters:
        trans_mat = results.regime_transition.copy()
        trans_matrix = trans_mat.T
        const_params = [results.params[f"const[{i}]"] for i in range(self.k_regimes)]
        
        if self.switching_variance:
            sigma2_params = [results.params[f"sigma2[{i}]"] for i in range(self.k_regimes)]
        else:
            sigma2_params = [results.params["sigma2"]] * self.k_regimes

        ar_list = []
        for i in range(self.k_regimes):
            regime_ar = []
            for lag in range(1, self.order + 1):
                param_name = f"ar.L{lag}[{i}]" if self.switching_ar else f"ar.L{lag}"
                regime_ar.append(results.params[param_name])
            ar_list.append(regime_ar)

        initial_probs = results.smoothed_marginal_probabilities[-1, :]

        return MarkovRegimeParameters(
            k_regimes=self.k_regimes,
            transition_matrix=np.array(trans_matrix),
            regime_means=np.array(const_params),
            regime_variances=np.array(sigma2_params),
            ar_coefficients=np.array(ar_list),
            initial_probabilities=np.array(initial_probs),
        )

    def simulate_regime_chain(self, n_steps: int, n_sims: int, random_state: Optional[int] = None) -> np.ndarray:
        if self.params_ is None:
            raise ValueError("Model must be fitted or parameters supplied before simulation.")

        rng = np.random.default_rng(random_state)
        p_matrix = self.params_.transition_matrix
        init_p = self.params_.initial_probabilities

        states = np.zeros((n_sims, n_steps + 1), dtype=int)
        states[:, 0] = [rng.choice(self.k_regimes, p=init_p) for _ in range(n_sims)]
        cum_p = np.cumsum(p_matrix, axis=1)

        for t in range(1, n_steps + 1):
            curr_states = states[:, t - 1]
            unif = rng.uniform(0.0, 1.0, size=n_sims)
            for r in range(self.k_regimes):
                mask = curr_states == r
                if np.any(mask):
                    states[mask, t] = np.searchsorted(cum_p[r], unif[mask])

        return states

class MertonJumpDiffusion:
    def __init__(self, params: MJDParameters):
        self.params = params

    def simulate(self, s0: float, t_years: float, n_steps: int, n_sims: int, random_state: Optional[int] = None) -> SimulationResult:
        rng = np.random.default_rng(random_state)
        dt = t_years / n_steps
        time_grid = np.linspace(0, t_years, n_steps + 1)

        drift_comp = (
            self.params.drift
            - 0.5 * (self.params.volatility ** 2)
            - self.params.jump_intensity * self.params.jump_compensator
        ) * dt

        z = rng.standard_normal(size=(n_sims, n_steps))
        brownian_inc = self.params.volatility * np.sqrt(dt) * z
        n_jumps = rng.poisson(lam=self.params.jump_intensity * dt, size=(n_sims, n_steps))
        
        jump_inc = np.zeros((n_sims, n_steps))
        for r_idx in range(n_sims):
            for c_idx in range(n_steps):
                k = n_jumps[r_idx, c_idx]
                if k > 0:
                    jump_inc[r_idx, c_idx] = np.sum(rng.normal(self.params.jump_mean, self.params.jump_std, size=k))

        log_increments = drift_comp + brownian_inc + jump_inc
        log_paths = np.zeros((n_sims, n_steps + 1))
        log_paths[:, 0] = np.log(s0)
        log_paths[:, 1:] = np.log(s0) + np.cumsum(log_increments, axis=1)

        paths = np.exp(log_paths)
        return SimulationResult(time_grid=time_grid, paths=paths)

class RegimeSwitchingMJD:
    def __init__(self, regime_params: MarkovRegimeParameters, regime_mjd_map: Dict[int, MJDParameters]):
        self.regime_params = regime_params
        self.regime_mjd_map = regime_mjd_map

    def simulate(self, s0: float, t_years: float, n_steps: int, n_sims: int, random_state: Optional[int] = None) -> SimulationResult:
        rng = np.random.default_rng(random_state)
        dt = t_years / n_steps
        time_grid = np.linspace(0, t_years, n_steps + 1)

        engine = MarkovRegimeEngine(k_regimes=self.regime_params.k_regimes)
        engine.params_ = self.regime_params
        state_paths = engine.simulate_regime_chain(n_steps=n_steps, n_sims=n_sims, random_state=random_state)

        log_paths = np.zeros((n_sims, n_steps + 1))
        log_paths[:, 0] = np.log(s0)

        for t in range(n_steps):
            current_states = state_paths[:, t]
            step_log_inc = np.zeros(n_sims)
            
            for r_id, mjd_param in self.regime_mjd_map.items():
                mask = (current_states == r_id)
                n_sub = int(np.sum(mask))
                if n_sub == 0:
                    continue

                drift_eff = (
                    mjd_param.drift
                    - 0.5 * (mjd_param.volatility ** 2)
                    - mjd_param.jump_intensity * mjd_param.jump_compensator
                ) * dt

                z = rng.standard_normal(size=n_sub)
                w_inc = mjd_param.volatility * np.sqrt(dt) * z
                j_counts = rng.poisson(lam=mjd_param.jump_intensity * dt, size=n_sub)
                
                j_inc = np.zeros(n_sub)
                for i_idx, count in enumerate(j_counts):
                    if count > 0:
                        j_inc[i_idx] = np.sum(rng.normal(mjd_param.jump_mean, mjd_param.jump_std, size=count))

                step_log_inc[mask] = drift_eff + w_inc + j_inc

            log_paths[:, t + 1] = log_paths[:, t] + step_log_inc

        paths = np.exp(log_paths)
        return SimulationResult(time_grid=time_grid, paths=paths, regimes=state_paths)
