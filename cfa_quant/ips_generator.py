"""
Institutional Investment Policy Statement (IPS) Generator
Constructs CFA Level III compliant Investment Policy Statements with:
1. Executive Summary & Family Governance Profile
2. Return Objective (Spending Rate + Inflation + Real Growth, Pre-Tax & After-Tax)
3. Risk Objective (Ability vs. Willingness Assessment)
4. Comprehensive Constraints (TTLLU: Time Horizon, Tax, Liquidity, Legal, Unique)
5. Strategic Asset Allocation (SAA) Targets & Rebalancing Corridors
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import json

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
    risk_willingness: str = "Moderate"  # 'Low', 'Moderate', 'Above Average', 'High'
    
    # TTLLU Constraints
    time_horizon_stages: List[str] = field(default_factory=lambda: ["Stage 1: Accumulation (7 years)", "Stage 2: Active Retirement (20+ years)"])
    liquidity_buffer_months: int = 12
    upcoming_lump_sum_distributions: List[Dict[str, Any]] = field(default_factory=list)
    legal_structures: List[str] = field(default_factory=lambda: ["Revocable Living Trust", "Durable Power of Attorney"])
    unique_mandates: List[str] = field(default_factory=lambda: ["ESG Screening", "Concentrated Position Risk Mitigation"])

class IpsGeneratorEngine:
    def __init__(self):
        pass

    def calculate_return_objective(self, profile: ClientProfile) -> Dict[str, Any]:
        """
        Calculates the required return:
        Spending Rate = Annual Spending / Portfolio Base
        After-Tax Real Return = Spending Rate + Real Capital Growth Target
        After-Tax Nominal Return = (1 + Real Return) * (1 + Inflation) - 1
        Pre-Tax Nominal Return = After-Tax Nominal / (1 - Effective Tax Rate)
        """
        spending_rate = profile.annual_spending_needs / max(profile.total_investable_assets, 1.0)
        
        # Real capital growth target (to preserve principal and grow bequest)
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
        # Quantitative Ability Score
        spending_ratio = profile.annual_spending_needs / max(profile.total_investable_assets, 1.0)
        
        if spending_ratio < 0.035 and profile.human_capital_type == "bond_like":
            ability = "Above Average"
            ability_rationale = "Low spending rate (<3.5%), secure bond-like human capital, and robust asset cushion relative to liabilities."
        elif spending_ratio < 0.055:
            ability = "Moderate"
            ability_rationale = "Moderate spending rate (3.5%-5.5%) with sufficient runway for intermediate market volatility."
        else:
            ability = "Below Average"
            ability_rationale = "High spending rate (>5.5%) or near-term liquidity calls significantly limit risk absorption capacity."
            
        # Hierarchy: Overall risk tolerance cannot exceed the lower of Ability and Willingness
        risk_rank = {"Below Average": 1, "Low": 1, "Moderate": 2, "Above Average": 3, "High": 4}
        inv_rank = {1: "Below Average", 2: "Moderate", 3: "Above Average", 4: "High"}
        
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

    def generate_strategic_asset_allocation(self, overall_risk_tolerance: str) -> Dict[str, Any]:
        """
        Assigns target SAA weights and rebalancing corridors based on overall risk tolerance.
        """
        allocations = {
            "High": {
                "Global Equities": {"target": 0.75, "corridor": [0.70, 0.80]},
                "Fixed Income & Cash": {"target": 0.15, "corridor": [0.10, 0.20]},
                "Alternative Assets / Real Estate": {"target": 0.10, "corridor": [0.06, 0.14]}
            },
            "Above Average": {
                "Global Equities": {"target": 0.65, "corridor": [0.60, 0.70]},
                "Fixed Income & Cash": {"target": 0.25, "corridor": [0.20, 0.30]},
                "Alternative Assets / Real Estate": {"target": 0.10, "corridor": [0.06, 0.14]}
            },
            "Moderate": {
                "Global Equities": {"target": 0.50, "corridor": [0.45, 0.55]},
                "Fixed Income & Cash": {"target": 0.40, "corridor": [0.35, 0.45]},
                "Alternative Assets / Real Estate": {"target": 0.10, "corridor": [0.06, 0.14]}
            },
            "Below Average": {
                "Global Equities": {"target": 0.30, "corridor": [0.25, 0.35]},
                "Fixed Income & Cash": {"target": 0.60, "corridor": [0.55, 0.65]},
                "Alternative Assets / Real Estate": {"target": 0.10, "corridor": [0.05, 0.15]}
            }
        }
        return allocations.get(overall_risk_tolerance, allocations["Moderate"])

    def generate_full_ips_document(self, profile: ClientProfile) -> str:
        """
        Generates a comprehensive, audit-ready Investment Policy Statement document in Markdown.
        """
        returns = self.calculate_return_objective(profile)
        risk = self.evaluate_risk_objective(profile)
        saa = self.generate_strategic_asset_allocation(risk["overall_risk_tolerance"])
        
        monthly_burn = profile.annual_spending_needs / 12.0
        emergency_reserve = monthly_burn * profile.liquidity_buffer_months
        
        ips_md = f"""# INSTITUTIONAL INVESTMENT POLICY STATEMENT (IPS)
**Client(s):** {profile.client_names}  
**Jurisdiction:** {profile.residence_jurisdiction}  
**Date of Adoption:** August 2026  
**Fiduciary Standard:** CFA Institute Standards of Professional Conduct  

---

## 1. Executive Summary & Family Governance Profile
- **Total Investable Assets:** ${profile.total_investable_assets:,.2f}
- **Client Ages:** {', '.join(map(str, profile.ages))}
- **Human Capital Asset Valuation:** ${profile.human_capital_value:,.2f} ({profile.human_capital_type.replace('_', ' ').title()})
- **Bequest / Legacy Target:** ${profile.bequest_legacy_goal:,.2f}

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

## 4. Investment Constraints (TTLLU Framework)

### A. Time Horizon
- **Structure:** Multi-Stage Horizon
- **Stages:**
"""
        for s in profile.time_horizon_stages:
            ips_md += f"  - {s}\n"
            
        ips_md += f"""
### B. Tax Considerations
- **Income Tax Rate:** {profile.effective_income_tax_rate*100:.1f}% | **Capital Gains Tax Rate:** {profile.capital_gains_tax_rate*100:.1f}%
- **Asset Location Policy:** High turnover and fixed income assets located in tax-deferred/exempt accounts; high-growth, buy-and-hold equities located in taxable accounts.

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

## 5. Strategic Asset Allocation (SAA) & Rebalancing Policy

| Asset Class | Target Allocation | Rebalancing Corridor |
| :--- | :--- | :--- |
"""
        for asset, data in saa.items():
            ips_md += f"| **{asset}** | **{data['target']*100:.1f}%** | [{data['corridor'][0]*100:.1f}%, {data['corridor'][1]*100:.1f}%] |\n"

        ips_md += """
- **Rebalancing Rules:** Portfolio is monitored quarterly and rebalanced whenever any asset class breaches its upper or lower corridor band.
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
        risk_willingness="Above Average"
    )
    
    gen = IpsGeneratorEngine()
    ips_text = gen.generate_full_ips_document(client)
    print("=" * 75)
    print("Generated CFA Level III Investment Policy Statement (IPS):")
    print("=" * 75)
    print(ips_text[:1200] + "\n... [Document truncated for preview] ...")
