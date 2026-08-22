"""
CFA Agentic Copilot Harness & Autonomous Workspace Engine
Equips the conversational assistant with:
1. Isolated File Read/Write Workspace (data/agent_workspace/)
2. Tool Calling Dispatcher across DCF, IPS, Macro Scenarios, SML, and Hybrid RAG
3. Execution Intent Routing & Multi-Turn Response Synthesis
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

try:
    from .rag_engine import HybridRagEngine
    from .ips_generator import IpsGeneratorEngine, ClientProfile
    from .scenario_lab import ScenarioLabEngine
    from .instruments.portfolio import UnifiedPortfolio
    from .instruments.fixed_income import FixedCouponBond
    from .instruments.equity import PublicEquityStock
except ImportError:
    try:
        from cfa_quant.rag_engine import HybridRagEngine
        from cfa_quant.ips_generator import IpsGeneratorEngine, ClientProfile
        from cfa_quant.scenario_lab import ScenarioLabEngine
        from cfa_quant.instruments.portfolio import UnifiedPortfolio
        from cfa_quant.instruments.fixed_income import FixedCouponBond
        from cfa_quant.instruments.equity import PublicEquityStock
    except ImportError:
        from rag_engine import HybridRagEngine
        from ips_generator import IpsGeneratorEngine, ClientProfile
        from scenario_lab import ScenarioLabEngine
        from instruments.portfolio import UnifiedPortfolio
        from instruments.fixed_income import FixedCouponBond
        from instruments.equity import PublicEquityStock

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

    def tool_search_cfa(self, query: str) -> str:
        results = self.rag.search_hybrid(query, top_k=3)
        if not results:
            return "No matching CFA curriculum items found."
        formatted = []
        for r in results:
            item_str = f"**[{r['level']}] {r['topic']} ➔ {r['subtopic']}**\n"
            if r.get("formulas"):
                item_str += f"*Formulas:*\n```\n{r['formulas']}\n```\n"
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
            return f"✗ Insufficient historical SEC statements for {ticker}."
            
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
        
        return f"""### 📊 CFA Valuation Memo: {ticker} ({sec_data['entity_name']})
- **Current Market Price:** ${spot:,.2f}
- **3-Stage DCF Intrinsic Value:** **${dcf['intrinsic_value_per_share']:,.2f}**
- **Margin of Safety (MoS):** **{mos:+.1f}%**
- **Dynamic WACC:** {wacc_res['wacc']*100:.2f}% (Rf: {rf*100:.2f}%, Beta: {mkt_data['beta']:.2f})
- **Valuation Stance:** {"UNDERVALUED (BUY)" if mos > 15.0 else ("FAIR VALUE (HOLD)" if mos >= -10.0 else "OVERVALUED (SELL)")}
"""

    def tool_run_stress_test(self, scenario_name: str = "stagflation_1970s") -> str:
        port = UnifiedPortfolio("Sample Client Wealth")
        port.add_instrument(PublicEquityStock("Global Equities", beta=1.0, expected_earnings_growth=0.07, historical_volatility=0.18), 6000000.0)
        port.add_instrument(FixedCouponBond("Core Treasuries", coupon_rate=0.040, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
        
        scenarios = {s["scenario_id"]: s for s in self.scenario_lab.hopper.list_all_scenarios()}
        sc = scenarios.get(scenario_name, scenarios.get("stagflation_1970s"))
        
        res = self.scenario_lab.run_portfolio_stress_test(port, sc["shocks"])
        return f"""### ⚡ Stress Test Simulation: {sc['scenario_name']}
- **Initial Portfolio Value:** ${res['portfolio_initial_value']:,.2f}
- **Projected Impact:** **{res['portfolio_impact_pct']:+.2f}%** (${res['portfolio_pnl_usd']:+,.2f})
- **Post-Shock Value:** **${res['portfolio_post_shock_value']:,.2f}**
- **Scenario Description:** {sc['description']}
"""

    def process_chat_message(self, user_prompt: str) -> Dict[str, Any]:
        p_lower = user_prompt.lower()
        tool_invoked = None
        
        if any(w in p_lower for w in ["value", "dcf", "valuation", "wacc", "intrinsic", "fair value"]):
            words = user_prompt.replace("?", "").replace(",", "").split()
            ticker_candidates = [w.upper() for w in words if w.isupper() and 1 <= len(w) <= 5]
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
            response_text = self.write_workspace_file(filename, f"# Research Note\nGenerated from prompt: {user_prompt}\n\nStrict adherence to CFA Standards.")
            
        else:
            tool_invoked = "HybridRagEngine(RRF Search)"
            response_text = self.tool_search_cfa(user_prompt)
            
        return {
            "response": response_text,
            "tool_invoked": tool_invoked
        }

if __name__ == "__main__":
    harness = CfaAgentHarness()
    print("=" * 70)
    print("🏛️ CFA AGENTIC COPILOT HARNESS TEST")
    print("=" * 70)
    
    msg1 = harness.process_chat_message("What is the valuation of MSFT?")
    print(f"Tool Invoked: {msg1['tool_invoked']}\n{msg1['response']}\n")
    
    msg2 = harness.process_chat_message("What happens in a 1970s stagflation shock?")
    print(f"Tool Invoked: {msg2['tool_invoked']}\n{msg2['response']}\n")
    print("=" * 70)
