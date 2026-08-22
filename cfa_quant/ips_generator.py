"""
Institutional Investment Policy Statement (IPS) Generator - CFA Level III Standards
Constructs comprehensive, audit-ready Investment Policy Statements with:
1. Executive Summary & Holistic Economic Balance Sheet (Financial Capital + Human Capital)
2. Return Objective (Spending Rate + Inflation + Real Growth, Pre-Tax & After-Tax)
3. Risk Objective (Ability vs. Willingness Assessment & Binding Constraints)
4. Comprehensive Constraints (TTLLU: Time Horizon, Tax, Liquidity, Legal, Unique)
5. Life-Cycle Stage Analysis & Age-Based Glidepath SAA
6. Goals-Based Wealth Management (GBWM) Sub-Portfolio Decomposition:
   - Lifestyle Protection Bucket
   - Aspirational Growth Bucket
   - Intergenerational Legacy / Bequest Bucket
7. Strategic Asset Allocation (SAA) Targets & Rebalancing Corridors
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json

try:
    from .lifecycle_portfolio import LifeCyclePortfolioEngine, LifeCycleClient
except ImportError:
    try:
        from cfa_quant.lifecycle_portfolio import LifeCyclePortfolioEngine, LifeCycleClient
    except ImportError:
        from lifecycle_portfolio import LifeCyclePortfolioEngine, LifeCycleClient

@dataclass
class ClientProfile:
    client_names: str
    ages: List[int]
    residence_jurisdiction: str
    total_investable_assets: float
    annual_spending_needs: float
    expected_inflation_rate: float = 0.025
    effective_income_tax_rate: float = 0.30
    capital_gains_tax_rate: float = 0.20
    bequest_legacy_goal: float = 0.0
    human_capital_value: float = 0.0
    human_capital_type: str = "bond_like"  # 'bond_like' or 'equity_like'
    
    # Risk Profile
    risk_willingness: str = "Moderate"  # 'Conservative', 'Moderate', 'Growth', 'Aggressive'
    
    # TTLLU Constraints
    time_horizon_stages: List[str] = field(default_factory=lambda: ["Stage 1: Accumulation (7 years)", "Stage 2: Active Retirement (20+ years)"])
    liquidity_buffer_months: int = 12
    upcoming_lump_sum_distributions: List[Dict[str, Any]] = field(default_factory=list)
    legal_structures: List[str] = field(default_factory=lambda: ["Revocable Living Trust", "Durable Power of Attorney"])
    unique_mandates: List[str] = field(default_factory=lambda: ["ESG Screening", "Concentrated Position Risk Mitigation"])

class IpsGeneratorEngine:
    def __init__(self, risk_free_rate: float = 0.045):
        self.rf = risk_free_rate
        self.lifecycle_engine = LifeCyclePortfolioEngine(risk_free_rate=risk_free_rate)

    def calculate_return_objective(self, profile: ClientProfile) -> Dict[str, Any]:
        """
        Calculates the required return:
        Spending Rate = Annual Spending / Portfolio Base
        After-Tax Real Return = Spending Rate + Real Capital Growth Target
        After-Tax Nominal Return = (1 + Real Return) * (1 + Inflation) - 1
        Pre-Tax Nominal Return = After-Tax Nominal / (1 - Effective Tax Rate)
        """
        spending_rate = profile.annual_spending_needs / max(profile.total_investable_assets, 1.0)
        
        real_growth_target = 0.010 if profile.bequest_legacy_goal > 0 else 0.005
        after_tax_real_return = spending_rate + real_growth_target
        after_tax_nominal_return = ((1.0 + after_tax_real_return) * (1.0 + profile.expected_inflation_rate)) - 1.0
        pre_tax_nominal_return = after_tax_nominal_return / (1.0 - profile.effective_income_tax_rate)
        
        return {
            "spending_rate_pct": round(spending_rate * 100, 2),
            "inflation_rate_pct": round(profile.expected_inflation_rate * 100, 2),
            "real_growth_target_pct": round(real_growth_target * 100, 2),
            "after_tax_nominal_required_pct": round(after_tax_nominal_return * 100, 2),
            "pre_tax_nominal_required_pct": round(pre_tax_nominal_return * 100, 2)
        }

    def evaluate_risk_objective(self, profile: ClientProfile) -> Dict[str, Any]:
        """
        Strict CFA Level III Risk Assessment:
        - Ability: Driven by wealth relative to spending, time horizon, human capital stability, liquidity demands.
        - Willingness: Subjective investor risk tolerance.
        - Overall: Constrained by min(Ability, Willingness).
        """
        spending_ratio = profile.annual_spending_needs / max(profile.total_investable_assets, 1.0)
        primary_age = profile.ages[0] if profile.ages else 50
        
        if spending_ratio < 0.035 and profile.human_capital_type == "bond_like":
            ability = "Aggressive" if primary_age < 45 else "Growth"
            ability_rationale = f"Low spending rate ({spending_ratio*100:.1f}%), secure bond-like human capital, and long investment horizon."
        elif spending_ratio < 0.055:
            ability = "Moderate"
            ability_rationale = f"Moderate spending rate ({spending_ratio*100:.1f}%) with solid buffer for market volatility."
        else:
            ability = "Conservative"
            ability_rationale = f"High spending rate ({spending_ratio*100:.1f}%) requires capital preservation focus."
            
        risk_rank = {"Conservative": 1, "Below Average": 1, "Moderate": 2, "Growth": 3, "Above Average": 3, "Aggressive": 4, "High": 4}
        inv_rank = {1: "Conservative", 2: "Moderate", 3: "Growth", 4: "Aggressive"}
        
        ability_val = risk_rank.get(ability, 2)
        willingness_val = risk_rank.get(profile.risk_willingness, 2)
        overall_val = min(ability_val, willingness_val)
        overall_tolerance = inv_rank[overall_val]
        
        return {
            "ability_to_take_risk": ability,
            "ability_rationale": ability_rationale,
            "willingness_to_take_risk": profile.risk_willingness,
            "overall_risk_tolerance": overall_tolerance,
            "binding_constraint": "Willingness" if willingness_val < ability_val else ("Ability" if ability_val < willingness_val else "Aligned")
        }

    def generate_full_ips_document(self, profile: ClientProfile) -> str:
        """
        Generates a comprehensive, audit-ready Investment Policy Statement document in Markdown.
        """
        returns = self.calculate_return_objective(profile)
        risk = self.evaluate_risk_objective(profile)
        
        primary_age = profile.ages[0] if profile.ages else 50
        lc_client = LifeCycleClient(
            client_name=profile.client_names,
            current_age=primary_age,
            human_capital_type=profile.human_capital_type,
            annual_living_expenses=profile.annual_spending_needs,
            current_financial_assets=profile.total_investable_assets,
            bequest_target_usd=profile.bequest_legacy_goal,
            risk_willingness=risk["overall_risk_tolerance"]
        )
        
        lc_profile = self.lifecycle_engine.generate_lifecycle_profile(lc_client)
        
        monthly_burn = profile.annual_spending_needs / 12.0
        emergency_reserve = monthly_burn * profile.liquidity_buffer_months
        
        ips_md = f"""# INSTITUTIONAL INVESTMENT POLICY STATEMENT (IPS)
**Client(s):** {profile.client_names}  
**Jurisdiction:** {profile.residence_jurisdiction}  
**Date of Adoption:** August 2026  
**Fiduciary Standard:** CFA Institute Standards of Professional Conduct  

---

## 1. Executive Summary & Holistic Economic Balance Sheet
- **Total Investable Financial Capital:** ${profile.total_investable_assets:,.2f}
- **Human Capital Present Value (PV):** ${lc_profile.human_capital_pv:,.2f} ({profile.human_capital_type.replace('_', ' ').title()})
- **Total Economic Net Worth:** **${lc_profile.total_economic_net_worth:,.2f}**
- **Human Capital Share of Total Wealth:** {lc_profile.human_capital_pct_of_wealth:.1f}%
- **Client Ages:** {', '.join(map(str, profile.ages))}
- **Life-Cycle Phase:** **{lc_profile.stage_name}** ({lc_profile.life_cycle_phase})
- **Bequest / Intergenerational Legacy Target:** ${profile.bequest_legacy_goal:,.2f}

---

## 2. Return Objectives
The investment portfolio must generate sufficient cash flow to cover annual living distributions while protecting the real purchasing power of the capital base against inflation.

- **Annual Spending Needs:** ${profile.annual_spending_needs:,.2f} (Spending Rate: **{returns['spending_rate_pct']:.2f}%**)
- **Expected Inflation (CPI):** {returns['inflation_rate_pct']:.2f}%
- **Real Capital Preservation / Growth:** {returns['real_growth_target_pct']:.2f}%
- **After-Tax Nominal Required Return:** **{returns['after_tax_nominal_required_pct']:.2f}%**
- **Pre-Tax Nominal Required Return:** **{returns['pre_tax_nominal_required_pct']:.2f}%** (at {profile.effective_income_tax_rate*100:.0f}% effective tax rate)

---

## 3. Risk Objectives & Risk Tolerance Profile
- **Ability to Take Risk:** **{risk['ability_to_take_risk']}**
  - *Rationale:* {risk['ability_rationale']}
- **Willingness to Take Risk:** **{risk['willingness_to_take_risk']}**
- **Overall Risk Tolerance:** **{risk['overall_risk_tolerance']}** (Binding Constraint: *{risk['binding_constraint']}*)

---

## 4. Goals-Based Wealth Management (GBWM) Sub-Portfolios

To optimize behavioral comfort and align cash flows with distinct liabilities, the investable wealth is partitioned into three discrete sub-portfolios:

| Goals-Based Sub-Portfolio | Target Dollar Amount | % of Portfolio | Primary Objective & Asset Implementation |
| :--- | :--- | :--- | :--- |
| **1. Lifestyle Protection Bucket** | **${lc_profile.goals_based_buckets.lifestyle_protection_usd:,.2f}** | **{lc_profile.goals_based_buckets.lifestyle_protection_pct:.1f}%** | 100% Capital Solvency & Essential Needs (Cash, Short Treasuries, TIPS & LDI Fixed Income) |
| **2. Aspirational Wealth Bucket** | **${lc_profile.goals_based_buckets.aspirational_growth_usd:,.2f}** | **{lc_profile.goals_based_buckets.aspirational_growth_pct:.1f}%** | Long-Term Capital Expansion (Global Large/Mid Equities & Private Capital) |
| **3. Legacy & Philanthropy Bucket**| **${lc_profile.goals_based_buckets.legacy_bequest_usd:,.2f}** | **{lc_profile.goals_based_buckets.legacy_bequest_pct:.1f}%** | Intergenerational Transfer & DAFs (Multi-Gen Compounders & Real Estate) |

---

## 5. Investment Constraints (TTLLU Framework)

### A. Time Horizon
- **Structure:** Multi-Stage Life Horizon ({lc_profile.time_horizon_years} Years Total Expected Runway)
- **Life-Cycle Stages:**
"""
        for s in profile.time_horizon_stages:
            ips_md += f"  - {s}\n"
            
        ips_md += f"""
### B. Tax Considerations
- **Income Tax Rate:** {profile.effective_income_tax_rate*100:.1f}% | **Capital Gains Tax Rate:** {profile.capital_gains_tax_rate*100:.1f}%
- **Asset Location Strategy:** 
  - *Taxable Accounts:* High-growth, low-turnover equities and municipal bonds.
  - *Tax-Deferred (Traditional 401k/IRA):* Taxable fixed income, REITs, and high-turnover strategies.
  - *Tax-Exempt (Roth):* Highest expected return equities and venture assets for maximum tax-free compounding.

### C. Liquidity Requirements
- **Immediate Liquidity Buffer:** **${emergency_reserve:,.2f}** ({profile.liquidity_buffer_months} months of operating expenses held in cash equivalents / Treasury Bills).
- **Upcoming Lump-Sum Calls:** None scheduled in the next 12 months.

### D. Legal & Regulatory Requirements
- **Governing Legal Framework:**
"""
        for l in profile.legal_structures:
            ips_md += f"  - {l}\n"
            
        ips_md += """
### E. Unique Circumstances & Governance Mandates
"""
        for u in profile.unique_mandates:
            ips_md += f"  - {u}\n"

        ips_md += f"""
---

## 6. Strategic Asset Allocation (SAA) Glidepath & Rebalancing Corridors

| Asset Class | Target Allocation | Rebalancing Corridor | Fiduciary Role |
| :--- | :--- | :--- | :--- |
| **Global Equities** | **{lc_profile.recommended_equity_pct:.1f}%** | [{max(0.0, lc_profile.recommended_equity_pct-5.0):.1f}%, {min(100.0, lc_profile.recommended_equity_pct+5.0):.1f}%] | Purchasing Power Growth & Real Return |
| **Fixed Income & LDI** | **{lc_profile.recommended_fixed_income_pct:.1f}%** | [{max(0.0, lc_profile.recommended_fixed_income_pct-5.0):.1f}%, {min(100.0, lc_profile.recommended_fixed_income_pct+5.0):.1f}%] | Deflation Hedge, Volatility Dampening & Cash Flow Matching |
| **Alternative Assets / Real Estate** | **{lc_profile.recommended_alternatives_pct:.1f}%** | [{max(0.0, lc_profile.recommended_alternatives_pct-4.0):.1f}%, {min(100.0, lc_profile.recommended_alternatives_pct+4.0):.1f}%] | Inflation Hedge & Uncorrelated Diversifier |

- **Rebalancing Rules:** Portfolio is reviewed quarterly and rebalanced whenever any major asset class breaches its corridor boundary, utilizing cash flow distributions to rebalance without triggering unnecessary taxable capital gains.
"""
        return ips_md

if __name__ == "__main__":
    client = ClientProfile(
        client_names="Dr. Charles & Evelyn Winslow",
        ages=[54, 52],
        residence_jurisdiction="United States (Florida / Tax-Exempt State)",
        total_investable_assets=7500000.0,
        annual_spending_needs=240000.0,
        expected_inflation_rate=0.025,
        effective_income_tax_rate=0.28,
        capital_gains_tax_rate=0.20,
        bequest_legacy_goal=3000000.0,
        human_capital_value=3200000.0,
        human_capital_type="bond_like",
        risk_willingness="Growth"
    )
    
    gen = IpsGeneratorEngine()
    ips_text = gen.generate_full_ips_document(client)
    print("=" * 75)
    print("Generated CFA Level III Investment Policy Statement (IPS):")
    print("=" * 75)
    print(ips_text[:1400] + "\n... [Document truncated for preview] ...")
