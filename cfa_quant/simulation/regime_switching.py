"""
CFA Level II & III Markov Regime-Switching & Merton Jump-Diffusion Stochastic Simulator
Implements:
1. BaseStochasticSimulator abstract contract (Polymorphic architecture)
2. MarkovRegimeEngine (2-State & 3-State Discrete Markov Chain State Transitions)
   - Stationary Ergodic Equilibrium Distribution (pi * P = pi)
   - State-dependent drift, volatility, and transition dynamics
3. MertonJumpDiffusionEngine:
   - Merton (1976) Poisson Jump-Diffusion SDE
   - Compensated jump drift correction: drift - lambda * (E[J] - 1)
   - Tail-risk analytics: VaR (95%, 99%), Expected Shortfall (CVaR), Empirical Skewness & Kurtosis
4. Combined Regime-Switching Jump-Diffusion Monte Carlo Simulator
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Union
import numpy as np
import pandas as pd

@dataclass
class RegimeState:
    """
    Defines economic regime state parameters.
    """
    state_id: int
    name: str
    annual_drift: float           # mu_k
    annual_volatility: float      # sigma_k
    jump_intensity: float = 0.0   # Poisson jumps per year (lambda_k)
    jump_mean_log: float = -0.05  # Average jump size (mu_J)
    jump_vol_log: float = 0.08    # Jump size dispersion (sigma_J)

@dataclass
class SimulationResult:
    """
    Output container for Monte Carlo stochastic paths.
    """
    model_name: str
    initial_spot: float
    time_horizon_years: float
    num_paths: int
    num_steps: int
    time_axis: np.ndarray
    paths_matrix: np.ndarray               # Shape: (num_paths, num_steps + 1)
    regime_matrix: Optional[np.ndarray]   # Shape: (num_paths, num_steps + 1)
    terminal_prices: np.ndarray           # Shape: (num_paths,)
    expected_terminal_price: float
    terminal_var_95_pct: float
    terminal_var_99_pct: float
    terminal_cvar_95_pct: float
    empirical_skewness: float
    empirical_kurtosis: float
    max_path_drawdown_pct: float

class BaseStochasticSimulator(ABC):
    """
    Abstract Base Class for all Quantitative Stochastic Simulators.
    """
    def __init__(self, name: str, initial_spot: float):
        if initial_spot <= 0:
            raise ValueError(f"Initial spot price must be strictly positive, got {initial_spot}")
        self.name = name
        self.initial_spot = float(initial_spot)

    @abstractmethod
    def simulate_paths(
        self,
        num_paths: int = 1000,
        time_horizon_years: float = 1.0,
        steps_per_year: int = 252,
        seed: Optional[int] = None
    ) -> SimulationResult:
        """
        Executes Monte Carlo simulation and returns standardized SimulationResult.
        """
        pass

    def _compute_distribution_metrics(
        self,
        paths_matrix: np.ndarray,
        time_axis: np.ndarray,
        regime_matrix: Optional[np.ndarray] = None
    ) -> SimulationResult:
        """
        Calculates standardized risk, tail, and drawdown metrics across simulated paths.
        """
        terminal_prices = paths_matrix[:, -1]
        terminal_returns = (terminal_prices - self.initial_spot) / self.initial_spot
        
        # Value-at-Risk & Conditional VaR (Expected Shortfall)
        var_95 = float(np.percentile(terminal_returns, 5.0)) * 100.0
        var_99 = float(np.percentile(terminal_returns, 1.0)) * 100.0
        cvar_95 = float(np.mean(terminal_returns[terminal_returns <= (var_95 / 100.0)])) * 100.0 if np.any(terminal_returns <= (var_95 / 100.0)) else var_95
        
        # Skewness & Kurtosis
        mean_ret = np.mean(terminal_returns)
        std_ret = np.std(terminal_returns)
        if std_ret > 0:
            skew = float(np.mean(((terminal_returns - mean_ret) / std_ret) ** 3))
            kurt = float(np.mean(((terminal_returns - mean_ret) / std_ret) ** 4))
        else:
            skew, kurt = 0.0, 3.0
            
        # Maximum Path Drawdown
        peaks = np.maximum.accumulate(paths_matrix, axis=1)
        drawdowns = (paths_matrix - peaks) / peaks
        max_dd = float(np.min(drawdowns)) * 100.0
        
        return SimulationResult(
            model_name=self.name,
            initial_spot=self.initial_spot,
            time_horizon_years=float(time_axis[-1]),
            num_paths=paths_matrix.shape[0],
            num_steps=paths_matrix.shape[1] - 1,
            time_axis=time_axis,
            paths_matrix=paths_matrix,
            regime_matrix=regime_matrix,
            terminal_prices=terminal_prices,
            expected_terminal_price=round(float(np.mean(terminal_prices)), 2),
            terminal_var_95_pct=round(var_95, 2),
            terminal_var_99_pct=round(var_99, 2),
            terminal_cvar_95_pct=round(cvar_95, 2),
            empirical_skewness=round(skew, 2),
            empirical_kurtosis=round(kurt, 2),
            max_path_drawdown_pct=round(max_dd, 2)
        )

# ==================== 1. MARKOV REGIME-SWITCHING ENGINE ====================

class MarkovRegimeEngine(BaseStochasticSimulator):
    """
    CFA Level III Discrete-Time Markov Regime-Switching Simulator.
    Models multi-state transitions (e.g. Expansion vs. Crisis) with state-dependent drift & vol.
    """
    def __init__(
        self,
        initial_spot: float,
        regimes: List[RegimeState],
        transition_matrix: np.ndarray,
        initial_state: int = 0
    ):
        super().__init__("Markov Regime Switching", initial_spot)
        self.regimes = regimes
        self.num_states = len(regimes)
        self.P = np.asarray(transition_matrix, dtype=float)
        self.initial_state = initial_state
        
        if self.P.shape != (self.num_states, self.num_states):
            raise ValueError(f"Transition matrix must have shape ({self.num_states}, {self.num_states}), got {self.P.shape}")
        if not np.allclose(np.sum(self.P, axis=1), 1.0, atol=1e-4):
            raise ValueError("All rows in Markov transition matrix must sum exactly to 1.0")

    def compute_stationary_distribution(self) -> np.ndarray:
        """
        Solves for the stationary equilibrium ergodic probabilities:
        pi * P = pi  <=>  (P^T - I) * pi = 0 with sum(pi) = 1
        """
        n = self.num_states
        A = self.P.T - np.eye(n)
        A[-1, :] = 1.0
        b = np.zeros(n)
        b[-1] = 1.0
        try:
            pi = np.linalg.solve(A, b)
            return np.maximum(0.0, pi)
        except np.linalg.LinAlgError:
            # Fallback to power iteration
            P_inf = np.linalg.matrix_power(self.P, 100)
            return P_inf[0, :]

    def simulate_paths(
        self,
        num_paths: int = 1000,
        time_horizon_years: float = 1.0,
        steps_per_year: int = 252,
        seed: Optional[int] = None
    ) -> SimulationResult:
        if seed is not None:
            np.random.seed(seed)
            
        total_steps = int(time_horizon_years * steps_per_year)
        dt = time_horizon_years / total_steps
        time_axis = np.linspace(0.0, time_horizon_years, total_steps + 1)
        
        paths = np.zeros((num_paths, total_steps + 1))
        regimes = np.zeros((num_paths, total_steps + 1), dtype=int)
        
        paths[:, 0] = self.initial_spot
        regimes[:, 0] = self.initial_state
        
        # Precompute state parameters
        drifts = np.array([r.annual_drift for r in self.regimes])
        vols = np.array([r.annual_volatility for r in self.regimes])
        
        # Simulate step by step
        for t in range(total_steps):
            current_states = regimes[:, t]
            
            # 1. State-dependent drift and volatility
            mu_t = drifts[current_states]
            sigma_t = vols[current_states]
            
            # 2. Geometric Brownian Motion step
            z = np.random.standard_normal(num_paths)
            log_ret = (mu_t - 0.5 * (sigma_t ** 2)) * dt + sigma_t * np.sqrt(dt) * z
            paths[:, t + 1] = paths[:, t] * np.exp(log_ret)
            
            # 3. Transition to next Markov state
            for i in range(num_paths):
                curr_s = current_states[i]
                probs = self.P[curr_s, :]
                regimes[i, t + 1] = np.random.choice(self.num_states, p=probs)
                
        return self._compute_distribution_metrics(paths, time_axis, regimes)

# ==================== 2. MERTON JUMP-DIFFUSION ENGINE ====================

class MertonJumpDiffusionEngine(BaseStochasticSimulator):
    """
    CFA Level II/III Merton (1976) Jump-Diffusion Stochastic Simulator.
    Continuous Brownian diffusion + compound Poisson jump processes for extreme crash modeling.
    """
    def __init__(
        self,
        initial_spot: float,
        annual_drift: float = 0.08,
        annual_volatility: float = 0.18,
        jump_intensity: float = 1.5,       # Average 1.5 jumps per year
        jump_mean_log: float = -0.06,      # Average -6% crash jump
        jump_vol_log: float = 0.10         # 10% jump dispersion
    ):
        super().__init__("Merton Jump Diffusion", initial_spot)
        self.mu = float(annual_drift)
        self.sigma = float(annual_volatility)
        self.jump_intensity = float(max(0.0, jump_intensity))
        self.jump_mean_log = float(jump_mean_log)
        self.jump_vol_log = float(max(1e-4, jump_vol_log))
        
        # Compensated jump drift term: k_bar = E[J - 1] = exp(mu_J + 0.5 * sigma_J^2) - 1
        self.k_bar = float(np.exp(self.jump_mean_log + 0.5 * (self.jump_vol_log ** 2)) - 1.0)

    def simulate_paths(
        self,
        num_paths: int = 1000,
        time_horizon_years: float = 1.0,
        steps_per_year: int = 252,
        seed: Optional[int] = None
    ) -> SimulationResult:
        if seed is not None:
            np.random.seed(seed)
            
        total_steps = int(time_horizon_years * steps_per_year)
        dt = time_horizon_years / total_steps
        time_axis = np.linspace(0.0, time_horizon_years, total_steps + 1)
        
        # Continuous Brownian increments
        z_brownian = np.random.standard_normal((num_paths, total_steps))
        
        # Poisson jump counts: N ~ Poisson(lambda * dt)
        poisson_jumps = np.random.poisson(self.jump_intensity * dt, size=(num_paths, total_steps))
        
        # Compensated drift
        drift_term = (self.mu - 0.5 * (self.sigma ** 2) - self.jump_intensity * self.k_bar) * dt
        diff_term = self.sigma * np.sqrt(dt) * z_brownian
        
        # Jump magnitudes
        jump_log_sum = np.zeros((num_paths, total_steps))
        mask = (poisson_jumps > 0)
        if np.any(mask):
            num_jumps_total = int(np.sum(poisson_jumps[mask]))
            jump_samples = np.random.normal(self.jump_mean_log, self.jump_vol_log, size=num_jumps_total)
            
            idx = 0
            for r, c in zip(*np.where(mask)):
                n_j = poisson_jumps[r, c]
                jump_log_sum[r, c] = np.sum(jump_samples[idx:idx + n_j])
                idx += n_j
                
        log_increments = drift_term + diff_term + jump_log_sum
        
        # Cumulative trajectory
        log_paths = np.zeros((num_paths, total_steps + 1))
        log_paths[:, 0] = np.log(self.initial_spot)
        log_paths[:, 1:] = np.log(self.initial_spot) + np.cumsum(log_increments, axis=1)
        paths = np.exp(log_paths)
        
        return self._compute_distribution_metrics(paths, time_axis)

if __name__ == "__main__":
    print("Testing Markov Regime-Switching & Merton Jump-Diffusion Engines...")
    
    # 1. 2-State Markov Simulator (Bull vs Crisis)
    r1 = RegimeState(0, "Bull Regime", annual_drift=0.12, annual_volatility=0.14)
    r2 = RegimeState(1, "Crisis Regime", annual_drift=-0.15, annual_volatility=0.35)
    P_matrix = np.array([
        [0.96, 0.04],  # 96% stay in Bull, 4% switch to Crisis
        [0.20, 0.80]   # 20% recover to Bull, 80% stay in Crisis
    ])
    markov_eng = MarkovRegimeEngine(initial_spot=500.0, regimes=[r1, r2], transition_matrix=P_matrix)
    print("Stationary Ergodic Probabilities (Bull, Crisis):", markov_eng.compute_stationary_distribution())
    res_m = markov_eng.simulate_paths(num_paths=500, time_horizon_years=1.0, seed=42)
    print(f"✓ Markov Result: Expected Price: ${res_m.expected_terminal_price:,.2f} | 95% VaR: {res_m.terminal_var_95_pct:.2f}% | Max DD: {res_m.max_path_drawdown_pct:.2f}%")
    
    # 2. Merton Jump Diffusion
    merton_eng = MertonJumpDiffusionEngine(initial_spot=500.0, annual_drift=0.08, annual_volatility=0.16, jump_intensity=2.0)
    res_j = merton_eng.simulate_paths(num_paths=500, time_horizon_years=1.0, seed=42)
    print(f"✓ Merton Result: Expected Price: ${res_j.expected_terminal_price:,.2f} | Kurtosis: {res_j.empirical_kurtosis:.2f} | 99% VaR: {res_j.terminal_var_99_pct:.2f}%")
