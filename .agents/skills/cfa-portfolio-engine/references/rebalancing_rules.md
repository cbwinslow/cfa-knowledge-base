# Institutional Rebalancing & Corridor Decision Rules

From CFA Level III Asset Allocation curriculum:

## Corridor Width Determinants

| Factor | Change in Factor | Effect on Optimal Corridor Width | CFA Rationale |
| :--- | :--- | :--- | :--- |
| **Transaction Costs** | Higher costs | **Wider** corridor | Avoid excessive trading drag / commissions |
| **Tax Rates** | Higher tax rate | **Wider** corridor | Avoid triggering taxable realized capital gains |
| **Risk Tolerance** | Higher tolerance | **Wider** corridor | Investor can tolerate larger tracking error & drift |
| **Asset Volatility** | Higher volatility | **Narrower** corridor | High vol assets drift rapidly; tight control required |
| **Correlation with rest of portfolio** | Higher correlation | **Wider** corridor | Assets move together; less impact on portfolio risk |

## Formula Formulation
$$\Delta w_i = \text{Base Width} \times \frac{(1 + 10 \cdot c) \cdot (1 + 0.8 \cdot \tau) \cdot (1 + 0.3 \cdot \rho)}{(1 + 2 \cdot \sigma)} \times \text{RiskMult}$$
