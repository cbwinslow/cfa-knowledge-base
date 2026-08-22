# CFA Level III Private & Institutional IPS Master Reference Manual

## 1. The Core Fiduciary IPS Framework

An Investment Policy Statement (IPS) is the formal, legally enforceable governing document that defines client objectives, constraints, and asset allocation policies under fiduciary law (Uniform Prudent Management of Institutional Funds Act - UPMIFA, ERISA, and CFA Standards).

---

## 2. Return Objective Formulation Across Multiple Investor Types

### A. Private High-Net-Worth Individual (HNWI)
$$\text{Spending Rate} = \frac{\text{Annual Distribution Needs}}{\text{Investable Portfolio Base}}$$
$$\text{After-Tax Real Return Requirement} = \text{Spending Rate} + \text{Real Growth Target}$$
$$\text{After-Tax Nominal Required Return} = (1 + \text{After-Tax Real Return})(1 + \text{Expected Inflation Rate}) - 1$$
$$\text{Pre-Tax Nominal Return} = \frac{\text{After-Tax Nominal Return}}{1 - t_{\text{effective}}}$$

### B. Endowments & Foundations (Spending Rules)
1. **Constant Growth Rule**:
   $$\text{Distribution}_t = \text{Distribution}_{t-1} \times (1 + \text{Inflation})$$
2. **Rolling Average (Three-Year Moving Average)**:
   $$\text{Distribution}_t = \text{Target Spending Rate} \times \left( \frac{1}{3} \sum_{i=1}^{3} \text{Asset Value}_{t-i} \right)$$
3. **Hybrid (Tobin-Yale) Rule**:
   $$\text{Distribution}_t = w \cdot [\text{Distribution}_{t-1} (1 + \pi_t)] + (1 - w) \cdot [\text{Target Spending Rate} \times \text{Asset Value}_{t-1}]$$

---

## 3. Risk Objectives: Rigorous Decomposition

### Ability to Take Risk (Objective Factors)
- **Time Horizon**: Long horizon ($>15$ years) increases ability to absorb drawdown.
- **Wealth relative to Outflows**: A spending rate $<3.5\%$ provides strong capital protection.
- **Human Capital Correlation**:
  - *Bond-like Human Capital*: Stable income (tenured doctor, judge) $\rightarrow$ High ability to take equity risk.
  - *Equity-like Human Capital*: Volatile income (startup founder, investment banker) $\rightarrow$ Lower ability to take equity risk; must avoid investing in same sector as employer.
- **Liquidity Buffer**: 12-24 months of cash reserves prevents forced selling in a bear market.

### Willingness to Take Risk (Subjective Behavioral Factors)
- Behavioral biases: Loss aversion, regret aversion, framing.
- Stated comfort level with portfolio volatility.

### The CFA Synthesis Rule:
$$\text{Overall Risk Tolerance} = \min(\text{Ability}, \text{Willingness})$$
*If Ability is High but Willingness is Low:* Advisor educates client, but **Willingness binds** to prevent client panic.  
*If Willingness is High but Ability is Low:* **Ability strictly binds** to protect financial solvency.

---

## 4. The TTLLU Constraints Architecture

1. **Time Horizon (T)**:
   - Identify discrete stages (e.g., Stage 1: Pre-Retirement Accumulation [8 years]; Stage 2: Retirement Decumulation [25 years]).
2. **Tax Considerations (T)**:
   - Account location optimization: Taxable (capital gains deferral) vs. Tax-deferred (ordinary income shelter) vs. Tax-exempt Roth (tax-free compounding).
3. **Liquidity Requirements (L)**:
   - Planned lump-sum expenditures (home purchase, college tuition, estate taxes) within 1-3 years held in cash equivalents.
4. **Legal & Regulatory (L)**:
   - Trusts (Revocable, Irrevocable, SLAT, GRAT), power of attorney, probate rules, SEC Rule 144 insider trading rules.
5. **Unique Circumstances (U)**:
   - Concentrated stock positions, ESG mandates, family governance disputes, foreign currency hedging.

---

## 5. Strategic Asset Allocation & Dynamic Rebalancing Corridors

Optimal corridor width around target weight $w_i$:
$$\text{Corridor Width} = f(\text{Transaction Costs}^+, \text{Risk Tolerance}^+, \text{Correlation to Portfolio}^+, \text{Asset Volatility}^-)$$
- **Wider Corridors**: High transaction costs, high client risk tolerance, high asset correlation with other portfolio components.
- **Narrower Corridors**: High asset volatility, low client risk tolerance, low transaction costs.
