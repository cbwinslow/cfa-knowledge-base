# CFA Knowledge Base & Quantitative Workspace Rules

## Operational Guidelines for Agents

1. **Standardized Valuation & Wealth Management**:
   - Always refer to official CFA Level I, II, and III curriculum standards when formulating investment policy statements (IPS), risk objectives (Ability vs. Willingness), and valuation models (DCF, Residual Income).
   - Use the local search utility (`python3 scripts/query_cfa_kb.py "<query>"`) to ground recommendations in exact formulas.

2. **Point-in-Time Data Integrity**:
   - When building backtests or screening models, ensure point-in-time financial statement alignment (avoid lookahead bias).

3. **Deterministic Math & Script Execution**:
   - For quantitative calculations (Human Capital PV, dynamic rebalancing corridors, WACC), execute the Python scripts in `.agents/skills/*/scripts/` rather than mental approximations.
