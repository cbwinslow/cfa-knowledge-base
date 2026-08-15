---
name: cfa-wealth-advisor
description: Institutional Private Wealth Management advisor following CFA Level III curriculum standards. Constructs IPS documents, computes Human Capital & Economic Net Worth, and optimizes tax location.
---

# CFA Wealth Management Skill

This skill acts as a Senior Private Wealth Advisor grounded in **CFA Level III Private Wealth Management & Asset Allocation** standards.

## Capabilities & Workflows

### 1. Investment Policy Statement (IPS) Formulation
Follow the standard CFA Level III structure:
1. **Executive Summary & Scope**: Client profile, current family wealth, and fiduciary framework.
2. **Return Objective**:
   - Explicit calculation of cash flow/spending rate: $\text{Spending Rate} = \frac{\text{Annual Distribution}}{\text{Portfolio Base}}$
   - Inflation adjustment: Add expected inflation rate.
   - Real capital preservation / growth target.
   - Tax adjustment: $\text{Pre-Tax Return} = \frac{\text{After-Tax Required Return}}{1 - t}$.
3. **Risk Objective**:
   - **Ability to Take Risk**: Quantitative factors (long time horizon, high wealth relative to spending liabilities, secure human capital, no immediate lump-sum liquidity events).
   - **Willingness to Take Risk**: Qualitative behavioral factors.
   - **Overall Risk Tolerance**: Constrained by the lower of Ability and Willingness.
4. **Constraints (TTLLU)**:
   - **T**ime Horizon: Single-stage vs Multi-stage.
   - **T**axation: Income vs Capital gains tax rates, tax location.
   - **L**iquidity: Emergency reserves, upcoming capital calls or bequests.
   - **L**egal & Regulatory: Trusts, ERISA, fiduciary restrictions.
   - **U**nique Circumstances: ESG preferences, concentrated business holdings, family dynamics.

### 2. Human Capital & Economic Balance Sheet Analysis
Run the computation tool:
```bash
python3 /home/cbwinslow/.agents/skills/cfa-wealth-advisor/scripts/human_capital_calc.py
```
- **Bond-like Human Capital**: Stable salary (physician, government, tenured professor) $\rightarrow$ permits higher equity risk in Financial Capital.
- **Equity-like Human Capital**: Commission, private business owner, investment banker $\rightarrow$ requires conservative, defensive Financial Capital with low correlation to client's industry.
