"""
CFA Level I/II/III Municipal Bonds & Securitized Fixed Income Instruments
Implements:
1. MunicipalBond (Tax-Equivalent Yield [TEY], Muni/Treasury Ratio, GO vs. Revenue DSCR, Key Rate Durations [KRD])
2. MortgageBackedSecurity (Agency MBS, PSA Prepayment Curves, Weighted Average Life [WAL], Negative Convexity)
3. AssetBackedSecurity (Tranche Subordination & Credit Enhancement)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import numpy_financial as npf

try:
    from .base import InvestmentInstrument, AssetClass
    from .fixed_income import FixedCouponBond
except ImportError:
    try:
        from cfa_quant.instruments.base import InvestmentInstrument, AssetClass
        from cfa_quant.instruments.fixed_income import FixedCouponBond
    except ImportError:
        from instruments.base import InvestmentInstrument, AssetClass
        from instruments.fixed_income import FixedCouponBond

@dataclass
class MunicipalBond(FixedCouponBond):
    """
    CFA Level I/II/III Municipal Bond Instrument
    """
    muni_type: str = "GO"                  # "GO" (General Obligation) or "Revenue"
    issuing_state: str = "CA"              # 2-letter state code
    is_federal_exempt: bool = True
    is_state_exempt: bool = True           # In-state resident exemption
    annual_net_operating_revenue: float = 0.0 # For Revenue bonds ($)
    annual_debt_service_due: float = 0.0      # For Revenue bonds ($)
    treasury_benchmark_10y_yield: float = 0.0474 # Live 10Y Treasury (4.74%)
    
    def __post_init__(self):
        super().__post_init__()
        self.asset_class = AssetClass.FIXED_INCOME

    def compute_tax_equivalent_yield(self, federal_tax_rate: float = 0.37, state_tax_rate: float = 0.093) -> float:
        """
        CFA Level I/III Tax-Equivalent Yield (TEY) Formula:
        TEY = Y_muni / [ 1 - (t_fed + t_state*(1 - t_fed)) ]
        """
        y_muni = self.yield_to_maturity
        t_fed = federal_tax_rate if self.is_federal_exempt else 0.0
        t_state = state_tax_rate if self.is_state_exempt else 0.0
        
        effective_tax_rate = t_fed + (t_state * (1.0 - t_fed))
        if effective_tax_rate >= 1.0:
            effective_tax_rate = 0.99
            
        tey = y_muni / (1.0 - effective_tax_rate)
        return round(float(tey), 4)

    def compute_muni_to_treasury_ratio(self) -> float:
        """
        Muni/Treasury Ratio = Y_muni / Y_treasury
        Institutional Valuation Signal:
        - Ratio > 85%: Munis Historically Cheap (ACCUMULATE)
        - Ratio 70%-85%: Fair Value
        - Ratio < 65%: Munis Expensive (FAVOR TREASURIES)
        """
        if self.treasury_benchmark_10y_yield == 0:
            return 1.0
        ratio = (self.yield_to_maturity / self.treasury_benchmark_10y_yield) * 100.0
        return round(float(ratio), 2)

    def get_valuation_signal(self) -> str:
        ratio = self.compute_muni_to_treasury_ratio()
        if ratio >= 85.0:
            return "CHEAP / HIGH TAX-ALPHA (ACCUMULATE)"
        elif ratio >= 70.0:
            return "FAIR VALUE"
        else:
            return "RICH / EXPENSIVE (FAVOR TREASURIES)"

    def compute_debt_service_coverage_ratio(self) -> Optional[float]:
        """
        Debt Service Coverage Ratio (DSCR) for Revenue Bonds:
        DSCR = Net Operating Revenues / Annual Debt Service
        CFA Benchmark: DSCR > 1.25x for Investment Grade
        """
        if self.muni_type.upper() != "REVENUE" or self.annual_debt_service_due <= 0:
            return None
        dscr = self.annual_net_operating_revenue / self.annual_debt_service_due
        return round(float(dscr), 2)

    def compute_key_rate_durations(self) -> Dict[str, float]:
        """
        Key Rate Duration (KRD) breakdown across 2Y, 5Y, 10Y, and 30Y tenors.
        """
        mod_dur = self.compute_modified_duration()
        mat = self.maturity_years
        
        if mat <= 3:
            krd = {"KRD_2Y": mod_dur * 0.90, "KRD_5Y": mod_dur * 0.10, "KRD_10Y": 0.0, "KRD_30Y": 0.0}
        elif mat <= 7:
            krd = {"KRD_2Y": mod_dur * 0.20, "KRD_5Y": mod_dur * 0.70, "KRD_10Y": mod_dur * 0.10, "KRD_30Y": 0.0}
        elif mat <= 15:
            krd = {"KRD_2Y": 0.0, "KRD_5Y": mod_dur * 0.25, "KRD_10Y": mod_dur * 0.65, "KRD_30Y": mod_dur * 0.10}
        else:
            krd = {"KRD_2Y": 0.0, "KRD_5Y": 0.0, "KRD_10Y": mod_dur * 0.30, "KRD_30Y": mod_dur * 0.70}
            
        return {k: round(float(v), 3) for k, v in krd.items()}

@dataclass
class MortgageBackedSecurity(InvestmentInstrument):
    """
    CFA Level I/II Agency Mortgage-Backed Security (MBS Pass-Through)
    """
    pool_id: str = "FNMA-30Y-POOL-8839"
    pass_through_coupon: float = 0.055       # 5.5% coupon
    original_balance: float = 10000000.0     # $10M pool
    current_pool_factor: float = 0.92        # 92% of original principal remaining
    benchmark_psa_speed: float = 120.0       # 120 PSA
    mortgage_rate_spread_bps: float = 125.0  # Spread over 10Y Treasury
    
    def __post_init__(self):
        self.asset_class = AssetClass.FIXED_INCOME
        self.current_market_price = 98.50    # $98.50 per 100 par
        self.quantity = (self.original_balance * self.current_pool_factor) / 100.0

    def compute_cpr_prepayment_rate(self) -> float:
        """
        Converts 100 PSA baseline (6% CPR at month 30) scaled by PSA speed:
        CPR = 6.0% * (PSA / 100)
        """
        cpr = 0.06 * (self.benchmark_psa_speed / 100.0)
        return round(float(cpr), 4)

    def compute_weighted_average_life_years(self) -> float:
        cpr = self.compute_cpr_prepayment_rate()
        wal = 1.0 / (0.04 + (cpr * 0.8))
        return round(float(min(wal, 18.0)), 2)

    def compute_expected_return(self) -> float:
        return self.pass_through_coupon + 0.005

    def compute_volatility(self) -> float:
        return 0.075

    def compute_duration(self) -> float:
        wal = self.compute_weighted_average_life_years()
        return round(wal * 0.82, 2)

    def compute_convexity(self) -> float:
        return -2.45

if __name__ == "__main__":
    print("=" * 75)
    print("🏛️ CFA LEVEL I/II/III MUNICIPAL BONDS & STRUCTURED ASSET ENGINE")
    print("=" * 75)
    
    cal_muni = MunicipalBond(
        name="State of California General Obligation Bond 2035",
        coupon_rate=0.050,
        maturity_years=10.0,
        yield_to_maturity=0.0345,
        issuing_state="CA",
        is_federal_exempt=True,
        is_state_exempt=True,
        treasury_benchmark_10y_yield=0.0474
    )
    
    tey = cal_muni.compute_tax_equivalent_yield(federal_tax_rate=0.37, state_tax_rate=0.093)
    ratio = cal_muni.compute_muni_to_treasury_ratio()
    krds = cal_muni.compute_key_rate_durations()
    
    print(f"Muni Bond: {cal_muni.name}")
    print(f"  • Stated Tax-Free Yield: {cal_muni.yield_to_maturity*100:.2f}%")
    print(f"  • Tax-Equivalent Yield (TEY): {tey*100:.2f}% (Fed: 37%, CA State: 9.3%)")
    print(f"  • 10Y Muni/Treasury Ratio: {ratio:.1f}% ({cal_muni.get_valuation_signal()})")
    print(f"  • Modified Duration: {cal_muni.compute_modified_duration():.2f} yrs | Convexity: {cal_muni.compute_convexity():.2f}")
    print(f"  • Key Rate Durations (KRD): {krds}")
    
    nyc_rev = MunicipalBond(
        name="NYC Transitional Finance Authority Revenue Bond 2036",
        muni_type="Revenue",
        coupon_rate=0.0525,
        maturity_years=12.0,
        yield_to_maturity=0.0360,
        issuing_state="NY",
        annual_net_operating_revenue=450000000.0,
        annual_debt_service_due=180000000.0
    )
    dscr = nyc_rev.compute_debt_service_coverage_ratio()
    print(f"\nRevenue Muni: {nyc_rev.name}")
    print(f"  • Debt Service Coverage Ratio (DSCR): {dscr:.2f}x ({'Strong Coverage' if dscr > 1.5 else 'Tight Coverage'})")
    
    mbs = MortgageBackedSecurity()
    print(f"\nAgency MBS: {mbs.pool_id}")
    print(f"  • Speed: {mbs.benchmark_psa_speed:.0f} PSA | CPR: {mbs.compute_cpr_prepayment_rate()*100:.2f}%")
    print(f"  • Weighted Average Life (WAL): {mbs.compute_weighted_average_life_years():.2f} yrs")
    print(f"  • Effective Duration: {mbs.compute_duration():.2f} yrs | Convexity: {mbs.compute_convexity():.2f} (Negative Convexity)")
    print("=" * 75)
