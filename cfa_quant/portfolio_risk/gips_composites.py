"""
CFA Level III & CIPM Institutional GIPS Compliance & Composite Reporting Engine
Implements:
1. True Daily Time-Weighted Rate of Return (TWRR) & Modified Dietz Approximation
2. Discretionary Account Composite Aggregation (Asset-Weighted & Equal-Weighted)
3. GIPS Internal Dispersion Metrics (Asset-Weighted Std Dev, High-Low Range, IQR)
4. Gross-of-Fees vs. Net-of-Fees Presentation with Tiered Model Fee Deduction
5. GIPS-Compliant Annual Presentation Table & Verification Metrics
"""

import math
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd

class GipsCompositeEngine:
    def __init__(self, composite_name: str = "US_LARGE_CAP_DISCRETIONARY_COMPOSITE"):
        self.composite_name = composite_name
        self.portfolios: Dict[str, Dict[str, Any]] = {}

    # ==================== STEP 1: RETURN METHODOLOGY CALCULATORS ====================
    @staticmethod
    def calculate_modified_dietz_return(
        beginning_market_value: float,
        ending_market_value: float,
        cash_flows: List[Tuple[float, int]],  # List of (cash_flow_amount, day_number)
        total_days_in_period: int = 30
    ) -> float:
        """
        Modified Dietz Formula (CFA Level III standard):
        R_md = (EMV - BMV - sum(CF_i)) / (BMV + sum(CF_i * W_i))
        where W_i = (CD - D_i) / CD
        """
        bmv = float(beginning_market_value)
        emv = float(ending_market_value)
        cd = float(total_days_in_period)
        
        sum_cf = sum(cf[0] for cf in cash_flows)
        sum_weighted_cf = sum(cf[0] * ((cd - cf[1]) / cd) for cf in cash_flows)
        
        denominator = bmv + sum_weighted_cf
        if abs(denominator) < 1e-6:
            return 0.0
            
        return (emv - bmv - sum_cf) / denominator

    @staticmethod
    def calculate_daily_twrr(sub_period_returns: List[float]) -> float:
        """
        True Daily Time-Weighted Rate of Return (TWRR):
        R_twrr = prod(1 + r_t) - 1
        """
        cum_factor = 1.0
        for r in sub_period_returns:
            cum_factor *= (1.0 + float(r))
        return cum_factor - 1.0

    # ==================== STEP 2: COMPOSITE AGGREGATION ====================
    def add_portfolio_period_data(
        self,
        portfolio_id: str,
        beginning_assets: float,
        ending_assets: float,
        gross_return: float,
        net_return: Optional[float] = None,
        annual_fee_bps: float = 50.0,
        is_discretionary: bool = True
    ):
        """
        Registers an account for composite inclusion (only discretionary accounts qualifying under GIPS).
        """
        if not is_discretionary:
            return  # Exclude non-discretionary portfolios per GIPS standards
            
        fee_rate = (annual_fee_bps / 10000.0) / 12.0  # Monthly fee approximation
        calc_net = net_return if net_return is not None else (gross_return - fee_rate)
        
        self.portfolios[portfolio_id] = {
            "portfolio_id": portfolio_id,
            "beginning_assets": float(beginning_assets),
            "ending_assets": float(ending_assets),
            "gross_return": float(gross_return),
            "net_return": float(calc_net),
            "fee_bps": float(annual_fee_bps)
        }

    def compute_composite_annual_performance(
        self,
        benchmark_annual_return: float = 0.085,
        total_firm_assets: float = 500000000.0
    ) -> Dict[str, Any]:
        """
        Computes asset-weighted composite return, internal dispersion, and creates GIPS presentation.
        """
        if not self.portfolios:
            return {"status": "error", "message": "No qualifying portfolios in composite"}

        df = pd.DataFrame(list(self.portfolios.values()))
        total_comp_bmv = df["beginning_assets"].sum()
        total_comp_emv = df["ending_assets"].sum()
        n_ports = len(df)
        
        # 1. Asset-Weighted Composite Returns (Beginning Assets Weighted)
        df["asset_weight"] = df["beginning_assets"] / total_comp_bmv
        composite_gross_return = float((df["gross_return"] * df["asset_weight"]).sum())
        composite_net_return = float((df["net_return"] * df["asset_weight"]).sum())
        equal_weighted_return = float(df["gross_return"].mean())

        # 2. GIPS Internal Dispersion Metrics (Only required if >= 5 portfolios)
        if n_ports >= 5:
            # Asset-Weighted Standard Deviation
            weighted_var = np.sum(df["asset_weight"] * ((df["gross_return"] - composite_gross_return) ** 2))
            asset_weighted_std = float(np.sqrt(weighted_var))
            
            # Equal-Weighted Standard Deviation
            equal_weighted_std = float(df["gross_return"].std(ddof=1))
            
            # High-Low Range
            high_low_spread = float(df["gross_return"].max() - df["gross_return"].min())
            
            # Interquartile Range (IQR)
            q75, q25 = np.percentile(df["gross_return"], [75, 25])
            iqr = float(q75 - q25)
        else:
            asset_weighted_std = 0.0
            equal_weighted_std = 0.0
            high_low_spread = float(df["gross_return"].max() - df["gross_return"].min()) if n_ports > 1 else 0.0
            iqr = 0.0

        # 3. Excess Return over Benchmark
        gross_excess = composite_gross_return - benchmark_annual_return
        net_excess = composite_net_return - benchmark_annual_return

        # 4. GIPS-Compliant Annual Presentation Table
        presentation_row = {
            "composite_name": self.composite_name,
            "number_of_portfolios": n_ports,
            "composite_gross_return_pct": round(composite_gross_return * 100, 2),
            "composite_net_return_pct": round(composite_net_return * 100, 2),
            "benchmark_return_pct": round(benchmark_annual_return * 100, 2),
            "gross_excess_return_pct": round(gross_excess * 100, 2),
            "net_excess_return_pct": round(net_excess * 100, 2),
            "internal_dispersion_std_pct": round(asset_weighted_std * 100, 2) if n_ports >= 5 else "N/A (<5 ports)",
            "high_low_spread_pct": round(high_low_spread * 100, 2),
            "composite_assets_usd": total_comp_emv,
            "total_firm_assets_usd": total_firm_assets,
            "composite_pct_of_firm": round((total_comp_emv / total_firm_assets) * 100, 2) if total_firm_assets > 0 else 0.0
        }

        return {
            "status": "success",
            "presentation": presentation_row,
            "portfolio_breakdown": df[["portfolio_id", "beginning_assets", "ending_assets", "gross_return", "net_return", "asset_weight"]].to_dict(orient="records"),
            "dispersion_details": {
                "asset_weighted_std": asset_weighted_std,
                "equal_weighted_std": equal_weighted_std,
                "high_low_spread": high_low_spread,
                "interquartile_range": iqr
            }
        }

if __name__ == "__main__":
    engine = GipsCompositeEngine("US_CORE_EQUITY_INSTITUTIONAL_COMPOSITE")
    
    # 1. Test Modified Dietz calculation
    # Account starts with $1,000,000, receives $200,000 on day 10 of 30, ends at $1,280,000
    r_md = engine.calculate_modified_dietz_return(
        beginning_market_value=1000000.0,
        ending_market_value=1280000.0,
        cash_flows=[(200000.0, 10)],
        total_days_in_period=30
    )
    print("=" * 80)
    print("🏛️ CFA / CIPM GIPS COMPOSITE REPORTING & PERFORMANCE ENGINE")
    print("=" * 80)
    print(f"✓ Modified Dietz Sub-Period Return: {r_md * 100:.2f}%")
    
    # 2. Add 6 Discretionary Client Portfolios
    ports = [
        ("PORT_A", 10000000.0, 11200000.0, 0.120),
        ("PORT_B", 25000000.0, 27750000.0, 0.110),
        ("PORT_C", 15000000.0, 16950000.0, 0.130),
        ("PORT_D", 8000000.0, 8880000.0, 0.110),
        ("PORT_E", 30000000.0, 33150000.0, 0.105),
        ("PORT_F", 12000000.0, 13380000.0, 0.115)
    ]
    for pid, bmv, emv, r_g in ports:
        engine.add_portfolio_period_data(pid, bmv, emv, gross_return=r_g, annual_fee_bps=65.0)
        
    res = engine.compute_composite_annual_performance(benchmark_annual_return=0.095, total_firm_assets=250000000.0)
    p = res["presentation"]
    print("\n✓ GIPS Annual Composite Presentation Table:")
    for k, v in p.items():
        print(f"  • {k:<30}: {v}")
    print("=" * 80)
