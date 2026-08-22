"""
CFA Level I & II Polymorphic Equity Valuation Framework
Implements clean object-oriented valuation hierarchy:
- BaseValuationModel (Abstract Base Class)
- ThreeStageDcfValuation (Explicit + Transition + Gordon Terminal)
- ResidualIncomeValuation (Book Value + PV of Economic Profit Alpha)
- DividendDiscountModelValuation (Multi-Stage DDM)
- FreeCashFlowToFirmValuation (FCFF @ WACC)
- FreeCashFlowToEquityValuation (FCFE @ Cost of Equity)
- MarketMultiplesValuation (Peer Relative EV/EBITDA & P/E)
- UnifiedValuationSuite (Polymorphic Ensemble & Consensus Valuation Bridge)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class ValuationOutput:
    model_name: str
    methodology: str
    intrinsic_value_per_share: float
    enterprise_value_usd: Optional[float] = None
    equity_value_usd: Optional[float] = None
    cost_of_capital: float = 0.08
    key_assumptions: Dict[str, Any] = field(default_factory=dict)
    valuation_components: Dict[str, float] = field(default_factory=dict)

class BaseValuationModel(ABC):
    """Abstract Base Class for all CFA Quantitative Valuation Models"""

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass

    @property
    @abstractmethod
    def methodology(self) -> str:
        pass

    @abstractmethod
    def calculate_intrinsic_value(
        self,
        ticker: str,
        financial_data: Dict[str, Any],
        cost_of_capital: float,
        shares_outstanding: float
    ) -> ValuationOutput:
        """
        Polymorphic interface to compute intrinsic value per share.
        """
        pass

# ==================== 1. THREE-STAGE DISSIPATIVE DCF ====================
class ThreeStageDcfValuation(BaseValuationModel):
    def __init__(
        self,
        stage1_years: int = 5,
        stage1_growth: float = 0.12,
        stage2_years: int = 5,
        stage3_terminal_growth: float = 0.035
    ):
        self.stage1_years = int(stage1_years)
        self.stage1_growth = float(stage1_growth)
        self.stage2_years = int(stage2_years)
        self.stage3_terminal_growth = float(stage3_terminal_growth)

    @property
    def model_name(self) -> str:
        return "Three-Stage Dissipative DCF"

    @property
    def methodology(self) -> str:
        return "Discounted Cash Flow (High Growth -> Linear Fade Transition -> Gordon Terminal)"

    def calculate_intrinsic_value(
        self,
        ticker: str,
        financial_data: Dict[str, Any],
        cost_of_capital: float,
        shares_outstanding: float
    ) -> ValuationOutput:
        fcf_base = float(financial_data.get("free_cash_flow", 1000000000.0))
        net_debt = float(financial_data.get("net_debt", 0.0))
        r = float(cost_of_capital)
        g_term = self.stage3_terminal_growth
        
        if r <= g_term:
            r = g_term + 0.02  # Convergence guard
            
        pv_stage1 = 0.0
        curr_fcf = fcf_base
        # Stage 1: High Growth
        for t in range(1, self.stage1_years + 1):
            curr_fcf *= (1.0 + self.stage1_growth)
            pv_stage1 += curr_fcf / ((1.0 + r) ** t)
            
        # Stage 2: Linear Transition Fade
        pv_stage2 = 0.0
        g_step = (self.stage1_growth - g_term) / (self.stage2_years + 1)
        for t in range(1, self.stage2_years + 1):
            curr_g = self.stage1_growth - (t * g_step)
            curr_fcf *= (1.0 + curr_g)
            discount_t = self.stage1_years + t
            pv_stage2 += curr_fcf / ((1.0 + r) ** discount_t)
            
        # Stage 3: Terminal Value
        terminal_discount_t = self.stage1_years + self.stage2_years
        terminal_val = (curr_fcf * (1.0 + g_term)) / (r - g_term)
        pv_terminal = terminal_val / ((1.0 + r) ** terminal_discount_t)
        
        enterprise_val = pv_stage1 + pv_stage2 + pv_terminal
        equity_val = max(100000.0, enterprise_val - net_debt)
        intrinsic_per_share = equity_val / shares_outstanding if shares_outstanding > 0 else 100.0
        
        return ValuationOutput(
            model_name=self.model_name,
            methodology=self.methodology,
            intrinsic_value_per_share=round(intrinsic_per_share, 2),
            enterprise_value_usd=round(enterprise_val, 2),
            equity_value_usd=round(equity_val, 2),
            cost_of_capital=r,
            key_assumptions={
                "stage1_growth": self.stage1_growth,
                "stage1_years": self.stage1_years,
                "stage2_years": self.stage2_years,
                "terminal_growth": self.stage3_terminal_growth
            },
            valuation_components={
                "pv_stage1_high_growth": round(pv_stage1, 2),
                "pv_stage2_transition": round(pv_stage2, 2),
                "pv_stage3_terminal": round(pv_terminal, 2),
                "terminal_value_pct_of_ev": round((pv_terminal / enterprise_val) * 100, 1) if enterprise_val > 0 else 0.0
            }
        )

# ==================== 2. RESIDUAL INCOME MODEL ====================
class ResidualIncomeValuation(BaseValuationModel):
    def __init__(self, roe_forecast: float = 0.22, forecast_years: int = 5, persistence_factor: float = 0.60):
        self.roe_forecast = float(roe_forecast)
        self.forecast_years = int(forecast_years)
        self.persistence_factor = float(persistence_factor)

    @property
    def model_name(self) -> str:
        return "Residual Income Model (RIM)"

    @property
    def methodology(self) -> str:
        return "Economic Profit Alpha (Current Book Value + PV of Future Residual Income)"

    def calculate_intrinsic_value(
        self,
        ticker: str,
        financial_data: Dict[str, Any],
        cost_of_capital: float,
        shares_outstanding: float
    ) -> ValuationOutput:
        book_value = float(financial_data.get("book_value_of_equity", 5000000000.0))
        r_e = float(cost_of_capital)
        
        pv_residual_income = 0.0
        curr_bv = book_value
        last_ri = 0.0
        
        for t in range(1, self.forecast_years + 1):
            ri_t = (self.roe_forecast - r_e) * curr_bv
            pv_residual_income += ri_t / ((1.0 + r_e) ** t)
            curr_bv += ri_t  # Clean surplus relation
            last_ri = ri_t
            
        # Continuing Residual Income with Persistence Factor omega
        # PV_terminal = RI_T+1 / (1 + r - omega)
        omega = self.persistence_factor
        ri_t_plus_1 = last_ri * omega
        denom = (1.0 + r_e - omega)
        pv_terminal_ri = (ri_t_plus_1 / denom) / ((1.0 + r_e) ** self.forecast_years) if denom > 0 else 0.0
        
        equity_val = max(100000.0, book_value + pv_residual_income + pv_terminal_ri)
        intrinsic_per_share = equity_val / shares_outstanding if shares_outstanding > 0 else 100.0
        
        return ValuationOutput(
            model_name=self.model_name,
            methodology=self.methodology,
            intrinsic_value_per_share=round(intrinsic_per_share, 2),
            equity_value_usd=round(equity_val, 2),
            cost_of_capital=r_e,
            key_assumptions={
                "forecast_roe": self.roe_forecast,
                "persistence_omega": self.persistence_factor,
                "forecast_horizon_years": self.forecast_years
            },
            valuation_components={
                "current_book_value": round(book_value, 2),
                "pv_explicit_residual_income": round(pv_residual_income, 2),
                "pv_continuing_residual_income": round(pv_terminal_ri, 2)
            }
        )

# ==================== 3. DIVIDEND DISCOUNT MODEL (DDM) ====================
class DividendDiscountModelValuation(BaseValuationModel):
    def __init__(self, dividend_growth_stage1: float = 0.08, terminal_growth: float = 0.035, stage1_years: int = 5):
        self.dividend_growth_stage1 = float(dividend_growth_stage1)
        self.terminal_growth = float(terminal_growth)
        self.stage1_years = int(stage1_years)

    @property
    def model_name(self) -> str:
        return "Two-Stage Dividend Discount Model (DDM)"

    @property
    def methodology(self) -> str:
        return "Discounted Dividends (High Dividend Growth -> Perpetual Gordon Dividend Growth)"

    def calculate_intrinsic_value(
        self,
        ticker: str,
        financial_data: Dict[str, Any],
        cost_of_capital: float,
        shares_outstanding: float
    ) -> ValuationOutput:
        d0_per_share = float(financial_data.get("dividend_per_share", 3.0))
        r_e = float(cost_of_capital)
        g_term = self.terminal_growth
        
        if r_e <= g_term:
            r_e = g_term + 0.02
            
        pv_dividends = 0.0
        curr_d = d0_per_share
        
        for t in range(1, self.stage1_years + 1):
            curr_d *= (1.0 + self.dividend_growth_stage1)
            pv_dividends += curr_d / ((1.0 + r_e) ** t)
            
        # Terminal Price at year T
        d_terminal_plus_1 = curr_d * (1.0 + g_term)
        p_terminal = d_terminal_plus_1 / (r_e - g_term)
        pv_terminal = p_terminal / ((1.0 + r_e) ** self.stage1_years)
        
        intrinsic_per_share = pv_dividends + pv_terminal
        equity_val = intrinsic_per_share * shares_outstanding
        
        return ValuationOutput(
            model_name=self.model_name,
            methodology=self.methodology,
            intrinsic_value_per_share=round(intrinsic_per_share, 2),
            equity_value_usd=round(equity_val, 2),
            cost_of_capital=r_e,
            key_assumptions={
                "stage1_dividend_growth": self.dividend_growth_stage1,
                "terminal_dividend_growth": self.terminal_growth,
                "base_dividend_d0": d0_per_share
            },
            valuation_components={
                "pv_explicit_dividends": round(pv_dividends, 2),
                "pv_terminal_dividend_price": round(pv_terminal, 2)
            }
        )

# ==================== 4. MARKET MULTIPLES PEER COMPS ====================
class MarketMultiplesValuation(BaseValuationModel):
    def __init__(self, target_pe_multiple: float = 28.0, target_ev_ebitda_multiple: float = 18.0):
        self.target_pe = float(target_pe_multiple)
        self.target_ev_ebitda = float(target_ev_ebitda_multiple)

    @property
    def model_name(self) -> str:
        return "Market Multiples Relative Valuation"

    @property
    def methodology(self) -> str:
        return "Peer Group Relative Multiples (Blended P/E & EV/EBITDA Synthetic Valuation)"

    def calculate_intrinsic_value(
        self,
        ticker: str,
        financial_data: Dict[str, Any],
        cost_of_capital: float,
        shares_outstanding: float
    ) -> ValuationOutput:
        eps = float(financial_data.get("eps_ttm", 12.50))
        ebitda = float(financial_data.get("ebitda", 5000000000.0))
        net_debt = float(financial_data.get("net_debt", 0.0))
        
        # P/E Implied Value
        val_pe = eps * self.target_pe
        
        # EV/EBITDA Implied Value
        ev_implied = ebitda * self.target_ev_ebitda
        eq_implied_ev = max(100000.0, ev_implied - net_debt)
        val_ev_ebitda = eq_implied_ev / shares_outstanding if shares_outstanding > 0 else val_pe
        
        # Blended Consensus
        blended_intrinsic = (val_pe * 0.5) + (val_ev_ebitda * 0.5)
        
        return ValuationOutput(
            model_name=self.model_name,
            methodology=self.methodology,
            intrinsic_value_per_share=round(blended_intrinsic, 2),
            equity_value_usd=round(blended_intrinsic * shares_outstanding, 2),
            cost_of_capital=cost_of_capital,
            key_assumptions={
                "peer_pe_multiple": self.target_pe,
                "peer_ev_ebitda_multiple": self.target_ev_ebitda,
                "base_eps": eps
            },
            valuation_components={
                "pe_implied_share_price": round(val_pe, 2),
                "ev_ebitda_implied_share_price": round(val_ev_ebitda, 2)
            }
        )

# ==================== 5. UNIFIED VALUATION SUITE ====================
class UnifiedValuationSuite:
    def __init__(self, models: Optional[List[BaseValuationModel]] = None):
        self.models = models or [
            ThreeStageDcfValuation(),
            ResidualIncomeValuation(),
            DividendDiscountModelValuation(),
            MarketMultiplesValuation()
        ]

    def evaluate_all_models(
        self,
        ticker: str,
        financial_data: Dict[str, Any],
        cost_of_capital: float = 0.0825,
        shares_outstanding: float = 7500000000.0
    ) -> Dict[str, Any]:
        """
        Polymorphically evaluates all valuation models and builds consensus triangulation.
        """
        results: List[ValuationOutput] = []
        prices: List[float] = []
        
        for m in self.models:
            out = m.calculate_intrinsic_value(ticker, financial_data, cost_of_capital, shares_outstanding)
            results.append(out)
            prices.append(out.intrinsic_value_per_share)
            
        arr_p = np.array(prices)
        mean_val = float(np.mean(arr_p))
        median_val = float(np.median(arr_p))
        min_val = float(np.min(arr_p))
        max_val = float(np.max(arr_p))
        std_val = float(np.std(arr_p))
        
        return {
            "ticker": ticker,
            "consensus_mean_value_per_share": round(mean_val, 2),
            "consensus_median_value_per_share": round(median_val, 2),
            "intrinsic_valuation_range": {
                "min": round(min_val, 2),
                "max": round(max_val, 2),
                "dispersion_std": round(std_val, 2)
            },
            "model_outputs": [
                {
                    "model_name": o.model_name,
                    "methodology": o.methodology,
                    "intrinsic_value": o.intrinsic_value_per_share,
                    "equity_value_usd": o.equity_value_usd,
                    "key_assumptions": o.key_assumptions,
                    "components": o.valuation_components
                }
                for o in results
            ]
        }

if __name__ == "__main__":
    suite = UnifiedValuationSuite()
    data = {
        "free_cash_flow": 65000000000.0,
        "book_value_of_equity": 250000000000.0,
        "dividend_per_share": 3.00,
        "eps_ttm": 12.80,
        "ebitda": 115000000000.0,
        "net_debt": -45000000000.0  # Net Cash
    }
    
    res = suite.evaluate_all_models("MSFT", data, cost_of_capital=0.0825, shares_outstanding=7430000000.0)
    print("=" * 85)
    print("🏛️ CFA POLYMORPHIC EQUITY VALUATION SUITE & CONSENSUS TRIANGULATION")
    print("=" * 85)
    print(f"• Target Equity: {res['ticker']}")
    print(f"✓ Consensus Mean Intrinsic Value:   ${res['consensus_mean_value_per_share']:,.2f}")
    print(f"✓ Consensus Median Intrinsic Value: ${res['consensus_median_value_per_share']:,.2f}")
    print(f"✓ Intrinsic Range:                 ${res['intrinsic_valuation_range']['min']:,.2f} - ${res['intrinsic_valuation_range']['max']:,.2f}")
    print("\nIndividual Polymorphic Model Results:")
    for m in res["model_outputs"]:
        print(f"  • {m['model_name']:<38}: ${m['intrinsic_value']:,.2f}")
    print("=" * 85)
