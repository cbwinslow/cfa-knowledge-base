---
name: cfa-portfolio-lab
description: Multi-portfolio comparative analytics, efficient frontier optimization, and macroeconomic stress-testing scenario lab based on CFA Level III asset allocation standards.
---

# CFA Portfolio Comparison & Stress-Testing Lab Skill

Use this skill whenever you need to compare two or more investment portfolios head-to-head, analyze asset allocation deltas, or simulate historical/hypothetical macroeconomic shocks (Stagflation, 2008 GFC, 2022 Rate Hikes, AI Booms).

## Workflows & Capabilities

### 1. Head-to-Head Portfolio Attribution
Runs comparative analysis between Portfolio A (e.g. Current Client Portfolio) and Portfolio B (e.g. Proposed CFA SAA):
- Expected Return Delta ($\text{bps}$) & Volatility Spread ($\sigma$)
- Sharpe Ratio, Sortino Ratio, and 95% Value-at-Risk ($\text{VaR}$)
- Macaulay Duration & Convexity mismatch

### 2. Macroeconomic Stress Testing
Simulates simultaneous P&L impact across 4 historical/hypothetical macro regimes:
- **1970s Stagflation Shock** ($\Delta \text{Inflation} = +300$ bps, $\Delta \text{Rates} = +250$ bps)
- **2008 Global Financial Crisis** (Equities $-38\%$, HY Spreads $+600$ bps, Flight to Treasuries $+12\%$)
- **2022 Rapid Monetary Tightening** (Equities $-19\%$, Fixed Income $-14\%$)
- **AI Productivity Boom** (Equities $+30\%$, Real GDP $+3.5\%$)

### 3. Execution CLI Script
```bash
python3 /home/cbwinslow/.agents/skills/cfa-portfolio-lab/scripts/run_stress_test.py
```
