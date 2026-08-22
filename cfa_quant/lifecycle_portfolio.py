"""
CFA Level III Life-Cycle Portfolio Construction & Goals-Based Wealth Allocation (GBWM)
Implements:
1. 4-Stage Life-Cycle Model (Early Career, Peak Accumulation, Pre-Retirement Transition, Decumulation)
2. Human Capital to Financial Capital Conversion & Total Economic Net Worth
3. Dynamic Age-Based Glidepath Engine (Year-by-Year Allocation up to Age 95)
4. Goals-Based Wealth Management (GBWM) 3-Bucket Sub-Portfolio Decomposition:
   - Essential Lifestyle Protection Bucket (LDI / Treasuries)
   - Aspirational Wealth Bucket (Global Equities / Private Equity)
   - Intergenerational Legacy / Bequest Bucket (Multi-Generational Growth)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go

@dataclass
class LifeCycleClient:
    client_name: str
    current_age: int
    retirement_target_age: int = 65
    life_expectancy_age: int = 92
    annual_employment_income: float = 250000.0
    human_capital_type: str = "bond_like"  # 'bond_like' or 'equity_like'
    annual_living_expenses: float = 120000.0
    current_financial_assets: float = 2000000.0
    bequest_target_usd: float = 1500000.0
    risk_willingness: str = "Moderate"     # 'Conservative', 'Moderate', 'Growth', 'Aggressive'

@dataclass
class GoalsBasedBuckets:
    lifestyle_protection_usd: float
    lifestyle_protection_pct: float
    lifestyle_asset_mix: Dict[str, float]
    
    aspirational_growth_usd: float
    aspirational_growth_pct: float
    aspirational_asset_mix: Dict[str, float]
    
    legacy_bequest_usd: float
    legacy_bequest_pct: float
    legacy_asset_mix: Dict[str, float]

@dataclass
class LifeCycleStageProfile:
    stage_name: str
    age_range: str
    life_cycle_phase: str
    time_horizon_years: int
    human_capital_pv: float
    financial_capital: float
    total_economic_net_worth: float
    human_capital_pct_of_wealth: float
    recommended_equity_pct: float
    recommended_fixed_income_pct: float
    recommended_alternatives_pct: float
    key_cfa_fiduciary_focus: List[str]
    goals_based_buckets: GoalsBasedBuckets

class LifeCyclePortfolioEngine:
    def __init__(self, risk_free_rate: float = 0.045, expected_equity_return: float = 0.080):
        self.rf = risk_free_rate
        self.eq_ret = expected_equity_return

    def estimate_human_capital_npv(self, client: LifeCycleClient, wage_growth_rate: float = 0.030) -> float:
        """
        Estimates the present value of future lifetime earnings discounted at:
        - Risk-Free Rate + 1.0% for bond-like human capital (tenured doctor, government, tenured professor)
        - Risk-Free Rate + 4.5% for equity-like human capital (startup founder, commissioned sales, trader)
        """
        years_to_retire = max(0, client.retirement_target_age - client.current_age)
        if years_to_retire == 0:
            return 0.0
            
        discount_rate = self.rf + (0.010 if client.human_capital_type == "bond_like" else 0.045)
        
        # Stream of future earnings
        periods = np.arange(1, years_to_retire + 1)
        projected_wages = client.annual_employment_income * ((1.0 + wage_growth_rate) ** periods)
        pv_factors = 1.0 / ((1.0 + discount_rate) ** periods)
        
        human_capital_npv = np.sum(projected_wages * pv_factors)
        return round(float(human_capital_npv), 2)

    def determine_life_cycle_stage(self, age: int) -> Tuple[str, str, str]:
        """
        CFA Level III 4 Life-Cycle Phases:
        1. Foundation / Early Career (< 35)
        2. Peak Accumulation (35 - 54)
        3. Pre-Retirement Transition (55 - 65)
        4. Decumulation / Retirement (65+)
        """
        if age < 35:
            return ("Stage 1: Foundation & Early Accumulation", "20-35", "High Human Capital, Aggressive Long-Horizon Growth")
        elif age < 55:
            return ("Stage 2: Peak Wealth Accumulation", "35-54", "Peak Earnings Conversion, Tax Location & Asset Growth")
        elif age <= 65:
            return ("Stage 3: Pre-Retirement Transition", "55-65", "Sequence-of-Returns Protection, De-Risking Glidepath")
        else:
            return ("Stage 4: Distribution & Decumulation", "65+", "Longevity & Cash Flow Matching, Intergenerational Legacy")

    def construct_goals_based_buckets(self, client: LifeCycleClient, hc_pv: float) -> GoalsBasedBuckets:
        """
        CFA Goals-Based Wealth Allocation: Decomposes total wealth into 3 risk-separated mental accounts:
        1. Lifestyle Protection (Essential Needs / Solvency)
        2. Aspirational Growth (Wealth Expansion)
        3. Legacy & Philanthropy (Bequest Target)
        """
        fin_assets = client.current_financial_assets
        years_in_retirement = max(10, client.life_expectancy_age - max(client.current_age, client.retirement_target_age))
        
        # 1. Essential Lifestyle Reserve (PV of Essential Retirement Expenses)
        # 15 years of essential spending discounted at Rf
        pv_lifestyle_need = client.annual_living_expenses * ((1.0 - (1.0 / ((1.0 + self.rf) ** min(years_in_retirement, 20)))) / self.rf)
        lifestyle_target = min(fin_assets * 0.60, max(fin_assets * 0.25, pv_lifestyle_need * 0.40))
        
        # 2. Legacy / Bequest Bucket
        legacy_target = min(client.bequest_target_usd, fin_assets * 0.35)
        
        # 3. Aspirational Growth Bucket (Remaining financial wealth)
        aspirational_target = max(0.0, fin_assets - lifestyle_target - legacy_target)
        
        # Normalized percentages
        total = lifestyle_target + aspirational_target + legacy_target
        p_life = lifestyle_target / total
        p_asp = aspirational_target / total
        p_leg = legacy_target / total
        
        return GoalsBasedBuckets(
            lifestyle_protection_usd=round(lifestyle_target, 2),
            lifestyle_protection_pct=round(p_life * 100, 1),
            lifestyle_asset_mix={"Cash & Short Treasuries": 0.30, "Investment Grade Corporate / LDI": 0.50, "TIPS (Inflation-Protected)": 0.20},
            
            aspirational_growth_usd=round(aspirational_target, 2),
            aspirational_growth_pct=round(p_asp * 100, 1),
            aspirational_asset_mix={"Global Large-Cap Equities": 0.55, "Small-Cap / Emerging Markets": 0.25, "Private Equity / Venture": 0.20},
            
            legacy_bequest_usd=round(legacy_target, 2),
            legacy_bequest_pct=round(p_leg * 100, 1),
            legacy_asset_mix={"Global Equities (Multi-Gen Growth)": 0.70, "Real Estate / Farmland": 0.20, "Dividend Growth": 0.10}
        )

    def generate_lifecycle_profile(self, client: LifeCycleClient) -> LifeCycleStageProfile:
        """
        Synthesizes the complete CFA Level III Life-Cycle Wealth & Allocation Profile.
        """
        hc_pv = self.estimate_human_capital_npv(client)
        total_economic_net_worth = client.current_financial_assets + hc_pv
        hc_pct = (hc_pv / total_economic_net_worth) * 100.0 if total_economic_net_worth > 0 else 0.0
        
        stage_name, age_range, phase_desc = self.determine_life_cycle_stage(client.current_age)
        time_horizon = max(5, client.life_expectancy_age - client.current_age)
        
        # Base Equity Glidepath determined by Age and Human Capital
        # Rule of Thumb: Equity % = (110 - Age) adjusted for Human Capital character
        base_eq = max(25.0, min(90.0, 110.0 - client.current_age))
        
        # Adjust for Human Capital nature:
        # Bond-like human capital allows +10% higher equities in Financial Assets
        # Equity-like human capital requires -10% lower equities to prevent double-exposure
        if client.human_capital_type == "bond_like" and hc_pct > 30.0:
            base_eq += 8.0
        elif client.human_capital_type == "equity_like":
            base_eq -= 8.0
            
        # Adjust for Risk Willingness
        willingness_adj = {"Conservative": -10.0, "Moderate": 0.0, "Growth": +5.0, "Aggressive": +10.0}
        final_eq = np.clip(base_eq + willingness_adj.get(client.risk_willingness, 0.0), 20.0, 90.0)
        
        final_alt = 10.0 if client.current_financial_assets >= 1500000.0 else 5.0
        final_fi = max(5.0, 100.0 - final_eq - final_alt)
        
        # Fiduciary Focus Points
        if client.current_age < 35:
            focus = [
                "Maximize high-beta equity compounding across tax-advantaged vehicles (Roth 401k/IRA).",
                "Ensure disability and term life insurance to protect irreplaceable Human Capital asset ($" + f"{hc_pv:,.0f}" + ").",
                "Maintain 3-6 month emergency cash reserve to prevent early retirement account liquidations."
            ]
        elif client.current_age < 55:
            focus = [
                "Execute Tax-Alpha asset location (Equities in Taxable, Corporate Debt in 401k/IRA).",
                "Establish Education 529 Trusts and Spousal Lifetime Access Trusts (SLAT) for estate tax exemption sheltering.",
                "Begin diversification away from employer concentrated stock/options."
            ]
        elif client.current_age <= 65:
            focus = [
                "Mitigate Sequence-of-Returns Risk: Build a 2-year cash/Treasury disbursement runway.",
                "Shift Fixed Income allocation toward Liability-Driven Investing (LDI) duration matching.",
                "Re-evaluate health care and long-term care insurance strategies."
            ]
        else:
            focus = [
                "Implement tax-efficient decumulation sequencing: Taxable accounts first, Tax-Deferred second, Roth last.",
                "Optimize Required Minimum Distributions (RMDs) and Qualified Charitable Distributions (QCDs).",
                "Execute intergenerational wealth transfer and irrevocable family trust governance."
            ]
            
        buckets = self.construct_goals_based_buckets(client, hc_pv)
        
        return LifeCycleStageProfile(
            stage_name=stage_name,
            age_range=age_range,
            life_cycle_phase=phase_desc,
            time_horizon_years=time_horizon,
            human_capital_pv=hc_pv,
            financial_capital=client.current_financial_assets,
            total_economic_net_worth=round(total_economic_net_worth, 2),
            human_capital_pct_of_wealth=round(hc_pct, 1),
            recommended_equity_pct=round(final_eq, 1),
            recommended_fixed_income_pct=round(final_fi, 1),
            recommended_alternatives_pct=round(final_alt, 1),
            key_cfa_fiduciary_focus=focus,
            goals_based_buckets=buckets
        )

    def generate_glidepath_trajectory(self, client: LifeCycleClient) -> pd.DataFrame:
        """
        Generates year-by-year asset allocation and Economic Balance Sheet trajectory from current age to Age 95.
        """
        trajectory = []
        start_age = client.current_age
        
        for age in range(start_age, 96):
            # Simulated dummy client at future age
            c_future = LifeCycleClient(
                client_name=client.client_name,
                current_age=age,
                retirement_target_age=client.retirement_target_age,
                life_expectancy_age=client.life_expectancy_age,
                annual_employment_income=client.annual_employment_income if age < client.retirement_target_age else 0.0,
                human_capital_type=client.human_capital_type,
                annual_living_expenses=client.annual_living_expenses,
                current_financial_assets=client.current_financial_assets,
                bequest_target_usd=client.bequest_target_usd,
                risk_willingness=client.risk_willingness
            )
            prof = self.generate_lifecycle_profile(c_future)
            
            trajectory.append({
                "Age": age,
                "Stage": prof.stage_name.split(":")[0],
                "Equity_Allocation_Pct": prof.recommended_equity_pct,
                "Fixed_Income_Allocation_Pct": prof.recommended_fixed_income_pct,
                "Alternatives_Allocation_Pct": prof.recommended_alternatives_pct,
                "Human_Capital_PV": prof.human_capital_pv,
                "Human_Capital_Share_Pct": prof.human_capital_pct_of_wealth
            })
            
        return pd.DataFrame(trajectory)

    def render_glidepath_figure(self, df_trajectory: pd.DataFrame, client_name: str) -> go.Figure:
        """
        Renders a stunning area chart showing the evolution of asset allocation across the entire life span.
        """
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_trajectory["Age"],
            y=df_trajectory["Equity_Allocation_Pct"],
            mode="lines",
            line=dict(width=0.5, color="#00E676"),
            stackgroup="one",
            name="Global Equities (%)"
        ))
        
        fig.add_trace(go.Scatter(
            x=df_trajectory["Age"],
            y=df_trajectory["Fixed_Income_Allocation_Pct"],
            mode="lines",
            line=dict(width=0.5, color="#2979FF"),
            stackgroup="one",
            name="Fixed Income & LDI (%)"
        ))
        
        fig.add_trace(go.Scatter(
            x=df_trajectory["Age"],
            y=df_trajectory["Alternatives_Allocation_Pct"],
            mode="lines",
            line=dict(width=0.5, color="#FFD700"),
            stackgroup="one",
            name="Alternative Assets / Real Estate (%)"
        ))
        
        fig.update_layout(
            title=f"📈 {client_name} Life-Cycle Asset Allocation Glidepath (Ages {df_trajectory['Age'].iloc[0]} to 95)",
            xaxis=dict(title="Investor Age (Years)", gridcolor="#333842"),
            yaxis=dict(title="Target Portfolio Allocation (%)", range=[0, 100], gridcolor="#333842"),
            template="plotly_dark",
            height=420,
            margin=dict(l=40, r=40, t=50, b=40)
        )
        
        return fig

if __name__ == "__main__":
    engine = LifeCyclePortfolioEngine()
    print("=" * 75)
    print("🏛️ CFA LEVEL III LIFE-CYCLE & GOALS-BASED WEALTH ENGINE")
    print("=" * 75)
    
    # Test Client: Age 42, Physician ($400k salary, $3.5M investable wealth)
    test_client = LifeCycleClient(
        client_name="Dr. Marcus Vance",
        current_age=42,
        retirement_target_age=65,
        annual_employment_income=400000.0,
        human_capital_type="bond_like",
        annual_living_expenses=180000.0,
        current_financial_assets=3500000.0,
        bequest_target_usd=2000000.0,
        risk_willingness="Growth"
    )
    
    profile = engine.generate_lifecycle_profile(test_client)
    print(f"Client: {test_client.client_name} (Age {test_client.current_age})")
    print(f"Life-Cycle Phase: {profile.stage_name} ({profile.age_range})")
    print(f"Financial Capital: ${profile.financial_capital:,.2f} | Human Capital NPV: ${profile.human_capital_pv:,.2f}")
    print(f"Total Economic Net Worth: ${profile.total_economic_net_worth:,.2f} (Human Capital Share: {profile.human_capital_pct_of_wealth}%)")
    print(f"\nRecommended SAA Glidepath Allocation:")
    print(f"  • Global Equities: {profile.recommended_equity_pct}%")
    print(f"  • Fixed Income & LDI: {profile.recommended_fixed_income_pct}%")
    print(f"  • Alternative Assets: {profile.recommended_alternatives_pct}%")
    
    print("\nGoals-Based Wealth Buckets (GBWM):")
    b = profile.goals_based_buckets
    print(f"  1. Lifestyle Protection Bucket: ${b.lifestyle_protection_usd:,.2f} ({b.lifestyle_protection_pct}%)")
    print(f"  2. Aspirational Growth Bucket:   ${b.aspirational_growth_usd:,.2f} ({b.aspirational_growth_pct}%)")
    print(f"  3. Legacy & Bequest Bucket:      ${b.legacy_bequest_usd:,.2f} ({b.legacy_bequest_pct}%)")
    print("=" * 75)
