---
name: cfa-portfolio-engine
description: Institutional Asset Allocation & Portfolio Planning engine based on CFA Level III curriculum. Implements Strategic/Tactical Asset Allocation, Black-Litterman, Rebalancing Corridors, and Performance Attribution.
---

# CFA Portfolio Planning & Asset Allocation Skill

This skill performs institutional-grade asset allocation and portfolio rebalancing workflows aligned with the **CFA Level III Portfolio Management** framework.

## Core Capabilities

### 1. Asset Allocation Frameworks
- **Strategic Asset Allocation (SAA)**: Target weights based on investor utility and long-term capital market expectations (CME).
- **Tactical Asset Allocation (TAA)**: Short-term deviations to exploit cyclical mispricings, governed by a strict tracking error budget.
- **Black-Litterman Model**: Overcomes Mean-Variance Optimization (MVO) corner solutions by blending market equilibrium returns with explicit subjective views.

### 2. Dynamic Rebalancing Corridors
Run the rebalancing calculation tool:
```bash
python3 /home/cbwinslow/.agents/skills/cfa-portfolio-engine/scripts/rebalance_corridor.py
```
- **Narrower Corridors**: Higher asset volatility (risk control).
- **Wider Corridors**: Higher transaction costs, higher tax friction, higher risk tolerance, higher correlation with other portfolio assets.

### 3. Performance Attribution (Brinson-Fachler Model)
- **Allocation Effect**: $A_i = (w_i - W_i) \cdot (B_i - B)$
- **Selection Effect**: $S_i = W_i \cdot (R_i - B_i)$
- **Interaction Effect**: $I_i = (w_i - W_i) \cdot (R_i - B_i)$
