#!/usr/bin/env python3
"""
CFA Quant Suite - Institutional Terminal User Interface (TUI)
Bloomberg / FactSet-style high-speed CLI terminal powered by Rich.
Anchored to Year 2026 Fiduciary Standards.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.prompt import Prompt
from rich.text import Text
from rich.markdown import Markdown

# Ensure root in path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from cfa_quant.agent_harness import CfaAgentHarness
from cfa_quant.scenario_lab import ScenarioLabEngine
from cfa_quant.excel_exporter import ExcelModelExporter
from cfa_quant.instruments.portfolio import UnifiedPortfolio
from cfa_quant.instruments.fixed_income import FixedCouponBond, InflationLinkedBond
from cfa_quant.instruments.equity import PublicEquityStock, RealEstateAsset
from pipeline.sec_edgar_client import SecEdgarClient
from pipeline.market_data import MarketDataClient
from pipeline.macro_engine import MacroEngine
from pipeline.cfa_valuation_engine import CfaValuationEngine
from pipeline.forensic_accounting import ForensicAccountingEngine
from pipeline.industry_benchmarks import IndustryBenchmarkEngine

console = Console()

class CfaTerminalApp:
    def __init__(self):
        self.harness = CfaAgentHarness()
        self.macro = MacroEngine()
        self.val_engine = CfaValuationEngine()
        self.forensic = ForensicAccountingEngine()
        self.bench = IndustryBenchmarkEngine()

    def render_header(self) -> Panel:
        macro_snap = self.macro.get_comprehensive_macro_snapshot()
        summary = macro_snap["macro_risk_summary"]
        
        hdr_text = Text()
        hdr_text.append("🏛️ CFA INSTITUTIONAL QUANTITATIVE TERMINAL", style="bold cyan")
        hdr_text.append(f"  |  YEAR: 2026  |  10Y YIELD: {summary['risk_free_rate_10y']}  |  SOFR: {summary['sofr_benchmark']}  |  HY SPREAD: {summary['credit_spread_hy_bps']}", style="bold yellow")
        return Panel(hdr_text, style="blue", expand=True)

    def run_ticker_valuation_view(self, ticker: str = "MSFT"):
        ticker = ticker.upper()
        sec = SecEdgarClient()
        mkt = MarketDataClient()
        
        with console.status(f"[bold green]Fetching SEC EDGAR filings and live market data for {ticker}..."):
            sec_data = sec.get_financial_history(ticker)
            mkt_data = mkt.get_market_quote(ticker)
            macro_snap = self.macro.get_comprehensive_macro_snapshot()
            rf = macro_snap["yield_curve"]["yields"]["10Y"]
            
        if not sec_data or len(sec_data["statements"]) < 2:
            console.print(f"[bold red]✗ Insufficient statements found for {ticker}.[/bold red]")
            return
            
        latest = sec_data["statements"][-1]
        prior = sec_data["statements"][-2]
        cfo = latest.get("operating_cash_flow", 0)
        capex = latest.get("capex", 0)
        cash = latest.get("cash_and_equivalents", 0)
        debt = latest.get("long_term_debt", 0) + latest.get("short_term_debt", 0)
        shares = mkt_data["shares_outstanding"]
        
        wacc_res = self.val_engine.compute_wacc(mkt_data["market_cap"], debt, mkt_data["beta"], rf)
        dcf = self.val_engine.compute_3stage_dcf(cfo, capex, cash, debt, shares, wacc_res["wacc"], 0.08)
        
        f_score = self.forensic.compute_piotroski_f_score(latest, prior)
        m_score = self.forensic.compute_beneish_m_score(latest, prior)
        sloan = self.forensic.compute_sloan_accruals(latest)
        ratios = self.bench.compute_cfa_ratios(latest)
        dp = ratios["dupont_5way"]
        
        # Valuation Summary Table
        t_val = Table(title=f"📊 Equity Valuation Memo: {ticker} ({sec_data['entity_name']})", expand=True)
        t_val.add_column("Metric", style="cyan", justify="left")
        t_val.add_column("Value (2026)", style="green", justify="right")
        t_val.add_column("Benchmark / Context", style="magenta", justify="left")
        
        spot = mkt_data["current_price"]
        dcf_val = dcf["intrinsic_value_per_share"]
        mos = ((dcf_val - spot) / dcf_val) * 100.0
        
        t_val.add_row("Current Spot Market Price", f"${spot:,.2f}", "Live 2026 Quote")
        t_val.add_row("3-Stage DCF Intrinsic Value", f"${dcf_val:,.2f}", f"Margin of Safety: {mos:+.1f}%")
        t_val.add_row("Dynamic WACC (Cost of Capital)", f"{wacc_res['wacc']*100:.2f}%", f"Rf: {rf*100:.2f}% | Beta: {mkt_data['beta']:.2f}")
        t_val.add_row("Piotroski F-Score", f"{f_score['piotroski_f_score']}/9", f_score['rating'])
        t_val.add_row("Beneish M-Score", f"{m_score['beneish_m_score']:.2f}", m_score['manipulation_risk'])
        t_val.add_row("Sloan Accruals Ratio", f"{sloan['sloan_accrual_ratio']:+.2f}%", sloan['earnings_quality'])
        console.print(t_val)
        
        # DuPont 5-Way Table
        t_dp = Table(title="🔬 DuPont 5-Way ROE Decomposition", expand=True)
        t_dp.add_column("Tax Burden (NI/EBT)", justify="center")
        t_dp.add_column("Interest Burden (EBT/EBIT)", justify="center")
        t_dp.add_column("EBIT Margin", justify="center")
        t_dp.add_column("Asset Turnover", justify="center")
        t_dp.add_column("Financial Leverage", justify="center")
        t_dp.add_column("Calculated ROE", style="bold green", justify="center")
        
        t_dp.add_row(
            f"{dp['tax_burden']:.3f}",
            f"{dp['interest_burden']:.3f}",
            f"{dp['ebit_margin']:.2f}%",
            f"{dp['asset_turnover']:.2f}x",
            f"{dp['financial_leverage']:.2f}x",
            f"{dp['roe_pct']:.2f}%"
        )
        console.print(t_dp)

    def run_portfolio_stress_view(self):
        port_curr = UnifiedPortfolio("Portfolio A (Traditional 60/40)")
        port_curr.add_instrument(PublicEquityStock("US Large Cap Equities", beta=1.0, expected_earnings_growth=0.065, historical_volatility=0.18), 6000000.0)
        port_curr.add_instrument(FixedCouponBond("Core Aggregate Bonds", coupon_rate=0.035, maturity_years=7.0, yield_to_maturity=0.045), 4000000.0)
        
        port_prop = UnifiedPortfolio("Portfolio B (CFA Institutional)")
        port_prop.add_instrument(PublicEquityStock("Global Compounders", beta=0.95, expected_earnings_growth=0.08, historical_volatility=0.16), 4000000.0)
        port_prop.add_instrument(FixedCouponBond("10Y Treasury LDI", coupon_rate=0.045, maturity_years=10.0, yield_to_maturity=0.0469), 2000000.0)
        port_prop.add_instrument(InflationLinkedBond("10Y TIPS Inflation Hedge", coupon_rate=0.020, maturity_years=10.0, yield_to_maturity=0.021), 1500000.0)
        port_prop.add_instrument(RealEstateAsset("Commercial Real Estate", net_operating_income=80000.0, cap_rate=0.055), 1500000.0)
        
        lab = ScenarioLabEngine()
        report = lab.compare_portfolios(port_curr, port_prop)
        
        t_stress = Table(title="⚡ Macroeconomic Stress Test & Portfolio Comparison", expand=True)
        t_stress.add_column("Macro Scenario", style="cyan")
        t_stress.add_column("Port A (60/40) P&L", style="red")
        t_stress.add_column("Port B (CFA SAA) P&L", style="green")
        t_stress.add_column("Resilience Advantage (Δ)", style="bold yellow")
        
        for _, row in report.stress_test_comparison.iterrows():
            t_stress.add_row(
                row["Macro Scenario"],
                f"{row[f'{port_curr.name} P&L ($)']} ({row[f'{port_curr.name} Impact (%)']})",
                f"{row[f'{port_prop.name} P&L ($)']} ({row[f'{port_prop.name} Impact (%)']})",
                row["Resilience Delta ($)"]
            )
        console.print(t_stress)

    def interactive_cli_loop(self):
        console.clear()
        console.print(self.render_header())
        
        while True:
            console.print("\n[bold cyan]Select Action:[/bold cyan] [1] Value Stock | [2] Macro Stress Test | [3] Ask CFA Copilot | [4] Exit")
            choice = Prompt.ask("Enter selection", choices=["1", "2", "3", "4"], default="1")
            
            if choice == "1":
                t = Prompt.ask("Enter Stock Ticker", default="MSFT")
                self.run_ticker_valuation_view(t)
            elif choice == "2":
                self.run_portfolio_stress_view()
            elif choice == "3":
                p = Prompt.ask("Ask CFA Copilot (Formulas, Addition Simulations, IPS)")
                with console.status("[bold green]Copilot reasoning with CFA tools..."):
                    res = self.harness.process_chat_message(p)
                console.print(Panel(Markdown(res["response"]), title=f"🤖 Copilot Tool: {res['tool_invoked'] or 'Hybrid RAG'}", border_style="green"))
            elif choice == "4":
                console.print("[bold yellow]Exiting CFA Terminal. Goodbye Charterholder![/bold yellow]")
                break

def main():
    app = CfaTerminalApp()
    if len(sys.argv) > 1 and sys.argv[1] == "--valuation":
        t = sys.argv[2] if len(sys.argv) > 2 else "MSFT"
        app.run_ticker_valuation_view(t)
    elif len(sys.argv) > 1 and sys.argv[1] == "--stress":
        app.run_portfolio_stress_view()
    else:
        app.interactive_cli_loop()

if __name__ == "__main__":
    main()
