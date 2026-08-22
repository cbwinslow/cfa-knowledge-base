"""
CFA Agentic Copilot Harness & Autonomous Workspace Engine
Year Anchored: 2026 | Fiduciary Standard: CFA Institute Code of Ethics & Standards of Professional Conduct

Capabilities:
1. Incremental Portfolio Asset Addition Simulation (e.g., "Add 1000 shares of AAPL")
2. CFA Rule-Bound Recommendations (Singer-Terhaar, Grinold-Kroner, Human Capital, LDI Immunization)
3. 3-Stage DCF & Residual Income Valuation (SEC EDGAR 10-K integration)
4. Macroeconomic Stress Testing (1970s Stagflation, 2008 GFC, 2022 Fed Hikes)
5. Isolated File Read/Write Workspace (data/agent_workspace/)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

try:
    from .rag_engine import HybridRagEngine
    from .ips_generator import IpsGeneratorEngine, ClientProfile
    from .scenario_lab import ScenarioLabEngine
    from .marginal_allocation import MarginalAllocationEngine
    from .instruments.portfolio import UnifiedPortfolio
    from .instruments.fixed_income import FixedCouponBond, InflationLinkedBond
    from .instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
except ImportError:
    try:
        from cfa_quant.rag_engine import HybridRagEngine
        from cfa_quant.ips_generator import IpsGeneratorEngine, ClientProfile
        from cfa_quant.scenario_lab import ScenarioLabEngine
        from cfa_quant.marginal_allocation import MarginalAllocationEngine
        from cfa_quant.instruments.portfolio import UnifiedPortfolio
        from cfa_quant.instruments.fixed_income import FixedCouponBond, InflationLinkedBond
        from cfa_quant.instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
    except ImportError:
        from rag_engine import HybridRagEngine
        from ips_generator import IpsGeneratorEngine, ClientProfile
        from scenario_lab import ScenarioLabEngine
        from marginal_allocation import MarginalAllocationEngine
        from instruments.portfolio import UnifiedPortfolio
        from instruments.fixed_income import FixedCouponBond, InflationLinkedBond
        from instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding

from pipeline.cfa_valuation_engine import CfaValuationEngine
from pipeline.sec_edgar_client import SecEdgarClient
from pipeline.market_data import MarketDataClient
from pipeline.macro_engine import MacroEngine

WORKSPACE_DIR = Path(__file__).resolve().parent.parent / "data" / "agent_workspace"

class CfaAgentHarness:
    def __init__(self, workspace_dir: Path = WORKSPACE_DIR):
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.rag = HybridRagEngine()
        self.val_engine = CfaValuationEngine()
        self.macro_engine = MacroEngine()
        self.ips_engine = IpsGeneratorEngine()
        self.scenario_lab = ScenarioLabEngine()
        self.marginal_engine = MarginalAllocationEngine()
        self.current_year = 2026

    # ==================== WORKSPACE FILE OPERATIONS ====================
    def write_workspace_file(self, filename: str, content: str) -> str:
        safe_name = Path(filename).name
        file_path = self.workspace_dir / safe_name
        with open(file_path, "w") as f:
            f.write(content)
        return f"✓ Successfully saved file to workspace: `{safe_name}` ({len(content)} bytes)"

    def read_workspace_file(self, filename: str) -> str:
        safe_name = Path(filename).name
        file_path = self.workspace_dir / safe_name
        if not file_path.exists():
            return f"✗ Error: File `{safe_name}` not found in workspace."
        with open(file_path, "r") as f:
            return f.read()

    def list_workspace_files(self) -> List[Dict[str, Any]]:
        files = []
        for p in self.workspace_dir.glob("*"):
            if p.is_file():
                files.append({
                    "filename": p.name,
                    "size_bytes": p.stat().st_size,
                    "last_modified": p.stat().st_mtime
                })
        return files

    # ==================== SPECIALIZED CFA TOOL CALLS ====================
    def tool_search_cfa(self, query: str) -> str:
        results = self.rag.search_hybrid(query, top_k=3)
        if not results:
            return "No matching CFA curriculum items found in the knowledge base."
        formatted = []
        for r in results:
            item_str = f"**[{r['level']}] {r['topic']} ➔ {r['subtopic']}**\n"
            if r.get("formulas"):
                item_str += f"*Formulas / Methodologies:*\n```\n{r['formulas']}\n```\n"
            item_str += f"{r['content']}\n"
            formatted.append(item_str)
        return "\n---\n".join(formatted)

    def tool_run_valuation(self, ticker: str, growth_stage1: float = 0.08) -> str:
        ticker = ticker.upper()
        sec = SecEdgarClient()
        mkt = MarketDataClient()
        
        sec_data = sec.get_financial_history(ticker)
        mkt_data = mkt.get_market_quote(ticker)
        macro_snap = self.macro_engine.get_comprehensive_macro_snapshot()
        rf = macro_snap["yield_curve"]["yields"]["10Y"]
        
        if not sec_data or len(sec_data["statements"]) < 2:
            return f"✗ Insufficient SEC statements available for {ticker}."
            
        latest = sec_data["statements"][-1]
        cfo = latest.get("operating_cash_flow", 0)
        capex = latest.get("capex", 0)
        cash = latest.get("cash_and_equivalents", 0)
        debt = latest.get("long_term_debt", 0) + latest.get("short_term_debt", 0)
        shares = mkt_data["shares_outstanding"]
        
        wacc_res = self.val_engine.compute_wacc(mkt_data["market_cap"], debt, mkt_data["beta"], rf)
        dcf = self.val_engine.compute_3stage_dcf(cfo, capex, cash, debt, shares, wacc_res["wacc"], growth_stage1)
        
        spot = mkt_data["current_price"]
        mos = ((dcf["intrinsic_value_per_share"] - spot) / dcf["intrinsic_value_per_share"]) * 100.0
        
        return f"""### 📊 CFA Level II Valuation Memo: {ticker} ({sec_data['entity_name']}) [2026 Analysis]
- **Current Spot Price (2026):** ${spot:,.2f}
- **3-Stage DCF Intrinsic Value:** **${dcf['intrinsic_value_per_share']:,.2f}**
- **Margin of Safety (MoS):** **{mos:+.1f}%**
- **Dynamic WACC:** {wacc_res['wacc']*100:.2f}% (10Y Rf: {rf*100:.2f}%, Beta: {mkt_data['beta']:.2f}, ERP: 5.0%)
- **Fiduciary Recommendation:** {"UNDERVALUED (ACCUMULATE)" if mos > 15.0 else ("FAIR VALUE (MARKET WEIGHT)" if mos >= -10.0 else "OVERVALUED / TRIM (TRIM POSITION)")}
"""

    def tool_simulate_portfolio_addition(self, ticker_or_asset: str, shares_or_dollars: float, is_shares: bool = True) -> str:
        """
        Simulates before-and-after impact of adding an investment to the client's portfolio.
        """
        ticker_or_asset = ticker_or_asset.upper()
        mkt = MarketDataClient()
        mkt_data = mkt.get_market_quote(ticker_or_asset)
        
        price = mkt_data.get("current_price", 100.0) if mkt_data else 100.0
        dollar_amount = (shares_or_dollars * price) if is_shares else shares_or_dollars
        
        # Base Portfolio ($10M Traditional 60/40)
        base_p = UnifiedPortfolio("Client Managed Wealth (Base)")
        base_p.add_instrument(PublicEquityStock("US Core Equities Index", beta=1.0, expected_earnings_growth=0.065, historical_volatility=0.18), 6000000.0)
        base_p.add_instrument(FixedCouponBond("Core US Aggregate Bonds", coupon_rate=0.035, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
        
        # Candidate Instrument
        cand = PublicEquityStock(
            name=f"{ticker_or_asset} Equity",
            ticker=ticker_or_asset,
            beta=mkt_data.get("beta", 1.05) if mkt_data else 1.05,
            dividend_yield=mkt_data.get("dividend_yield", 0.01) if mkt_data else 0.01,
            expected_earnings_growth=0.085,
            historical_volatility=mkt_data.get("volatility", 0.22) if mkt_data else 0.22
        )
        
        sim_res, _, _, _ = self.marginal_engine.simulate_asset_addition(base_p, cand, dollar_to_add=dollar_amount)
        
        return f"""### ➕ Portfolio Addition Simulation: +{shares_or_dollars:,.0f} shs {ticker_or_asset} (${dollar_amount:,.2f})
- **Added Allocation Weight:** {sim_res.added_weight_pct:.2f}% of Total Wealth (${sim_res.metrics_after['total_value_usd']:,.2f})

#### Pre- vs. Post-Allocation Metrics:
| Metric | Pre-Allocation (Before) | Post-Allocation (After) | Delta (Δ) |
| :--- | :--- | :--- | :--- |
| **Expected Annual Return** | {sim_res.metrics_before['expected_annual_return_pct']:.2f}% | {sim_res.metrics_after['expected_annual_return_pct']:.2f}% | **{sim_res.delta_metrics['return_delta_bps']:+.1f} bps/yr** |
| **Annualized Volatility (σ)** | {sim_res.metrics_before['annual_volatility_pct']:.2f}% | {sim_res.metrics_after['annual_volatility_pct']:.2f}% | **{sim_res.delta_metrics['volatility_delta_bps']:+.1f} bps** |
| **Portfolio Sharpe Ratio** | {sim_res.metrics_before['sharpe_ratio']:.2f} | {sim_res.metrics_after['sharpe_ratio']:.2f} | **{sim_res.delta_metrics['sharpe_delta']:+.2f}** |
| **1-Year 95% Value-at-Risk** | ${sim_res.metrics_before['total_value_usd']*(sim_res.metrics_before['var_95_pct_1yr']/100):,.2f} | ${sim_res.metrics_after['total_value_usd']*(sim_res.metrics_after['var_95_pct_1yr']/100):,.2f} | **${sim_res.delta_metrics['var_95_delta_usd']:+,.2f}** |
| **Diversification Benefit** | - | - | **{sim_res.diversification_benefit_pct:.1f}% Risk Reduction** |

**CFA Fiduciary Assessment:**
> {sim_res.recommendation_verdict}
"""

    def tool_run_stress_test(self, scenario_name: str = "stagflation_1970s") -> str:
        port = UnifiedPortfolio("Sample Client Wealth")
        port.add_instrument(PublicEquityStock("Global Equities", beta=1.0, expected_earnings_growth=0.07, historical_volatility=0.18), 6000000.0)
        port.add_instrument(FixedCouponBond("Core Treasuries", coupon_rate=0.040, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
        
        scenarios = {s["scenario_id"]: s for s in self.scenario_lab.hopper.list_all_scenarios()}
        sc = scenarios.get(scenario_name, scenarios.get("stagflation_1970s"))
        
        res = self.scenario_lab.run_portfolio_stress_test(port, sc["shocks"])
        return f"""### ⚡ Stress Test Simulation: {sc['scenario_name']} [2026 Macro Lens]
- **Initial Portfolio Capital:** ${res['portfolio_initial_value']:,.2f}
- **Projected Net Impact:** **{res['portfolio_impact_pct']:+.2f}%** (${res['portfolio_pnl_usd']:+,.2f})
- **Post-Shock Capitalization:** **${res['portfolio_post_shock_value']:,.2f}**
- **Regime Dynamics:** {sc['description']}
"""

    # ==================== MAIN CHAT ROUTER ====================
    def process_chat_message(self, user_prompt: str) -> Dict[str, Any]:
        p_lower = user_prompt.lower()
        tool_invoked = None
        
        # 1. Check for Incremental Portfolio Addition: "add 1000 shares of AAPL", "add $500k of MSFT"
        if ("add" in p_lower or "adding" in p_lower or "change if" in p_lower) and ("share" in p_lower or "$" in p_lower or "stock" in p_lower or "portfolio" in p_lower):
            # Extract number of shares or dollars
            num_match = re.search(r'(\d[\d,]*)', user_prompt)
            amt = float(num_match.group(1).replace(',', '')) if num_match else 1000.0
            
            # Extract ticker
            words = user_prompt.replace("?", "").replace(",", "").split()
            ticker_candidates = [w.upper() for w in words if w.isupper() and 1 <= len(w) <= 5 and w not in ["ADD", "AND", "THE", "FOR", "IF", "CFA", "IPS"]]
            target_t = ticker_candidates[0] if ticker_candidates else "AAPL"
            
            is_shs = "$" not in user_prompt
            tool_invoked = f"MarginalAllocationEngine(Add {amt:.0f} {'shs' if is_shs else '$'} {target_t})"
            response_text = self.tool_simulate_portfolio_addition(target_t, amt, is_shares=is_shs)
            
        elif any(w in p_lower for w in ["value", "dcf", "valuation", "wacc", "intrinsic", "fair value"]):
            words = user_prompt.replace("?", "").replace(",", "").split()
            ticker_candidates = [w.upper() for w in words if w.isupper() and 1 <= len(w) <= 5 and w not in ["VALUE", "DCF", "WACC", "CFA"]]
            target_t = ticker_candidates[0] if ticker_candidates else "MSFT"
            tool_invoked = f"CfaValuationEngine({target_t})"
            response_text = self.tool_run_valuation(target_t)
            
        elif any(w in p_lower for w in ["stress", "crash", "stagflation", "crisis", "shock", "scenario"]):
            tool_invoked = "ScenarioLabEngine(StressTest)"
            sc_id = "stagflation_1970s" if "stagflation" in p_lower else ("gfc_2008" if "2008" in p_lower or "crisis" in p_lower else "rate_hike_2022")
            response_text = self.tool_run_stress_test(sc_id)
            
        elif any(w in p_lower for w in ["save", "write", "memo", "workspace"]) and ("file" in p_lower or "save" in p_lower):
            tool_invoked = "WorkspaceManager(Write)"
            filename = "research_memo.md"
            response_text = self.write_workspace_file(filename, f"# Institutional Research Note (Year: {self.current_year})\nGenerated from prompt: {user_prompt}\n\nStrict adherence to CFA Standards.")
            
        else:
            tool_invoked = "HybridRagEngine(RRF Search)"
            response_text = self.tool_search_cfa(user_prompt)
            
        return {
            "response": response_text,
            "tool_invoked": tool_invoked
        }

if __name__ == "__main__":
    harness = CfaAgentHarness()
    print("=" * 75)
    print("🏛️ CFA AGENTIC COPILOT HARNESS (2026 FIDUCIARY STANDARDS)")
    print("=" * 75)
    
    # Test 1: Incremental Asset Addition ("Add 1000 shares of AAPL")
    msg1 = harness.process_chat_message("show me how my portfolio would change if we added 1000 shares of AAPL to our portfolio")
    print(f"Tool Invoked: {msg1['tool_invoked']}\n{msg1['response']}\n")
    print("=" * 75)
