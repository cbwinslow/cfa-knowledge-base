#!/usr/bin/env python3
"""
CFA Fundamental Valuation, Macro Regime & Industry Benchmark CLI
Orchestrates:
1. SEC EDGAR 10-K Ingestion
2. Macroeconomic & Yield Curve Regime Ingestion (SOFR, 10Y-3M Spread, Inflation)
3. 3-Stage DCF & Residual Income Valuation
4. DuPont 5-Way & Cash Conversion Cycle Ratio Analysis
5. Cross-Sectional Competitor Benchmarking
6. CAPM & Security Market Line (SML) Positioning
"""

import sys
import os
from pathlib import Path
from tabulate import tabulate

from sec_edgar_client import SecEdgarClient
from market_data import MarketDataClient
from macro_engine import MacroEngine
from industry_benchmarks import IndustryBenchmarkEngine
from capm_sml_model import CapmSmlModel
from cfa_valuation_engine import CfaValuationEngine
from forensic_accounting import ForensicAccountingEngine
from db_storage import init_valuation_db, save_company_valuation
from cfa_quant.excel_exporter import ExcelModelExporter

def run_valuation_for_ticker(ticker: str, growth_stage1: float = 0.08):
    ticker = ticker.upper()
    print("=" * 85)
    print(f"📊 INITIATING INSTITUTIONAL CFA VALUATION & BENCHMARK PIPELINE: {ticker}")
    print("=" * 85)
    
    # 1. Fetch Macroeconomic & Yield Curve Snapshot
    print(f"[1/6] Ingesting Live Macro Regime, SOFR Benchmark & Yield Curve...")
    macro_eng = MacroEngine()
    macro_snap = macro_eng.get_comprehensive_macro_snapshot()
    curve_regime = macro_snap["macro_risk_summary"]["curve_status"]
    rf = macro_snap["yield_curve"]["yields"]["10Y"]
    sofr = macro_snap["monetary_policy"]["sofr_rate"]
    print(f"      Yield Curve Status: {curve_regime}")
    print(f"      10-Yr US Treasury (Rf): {rf*100:.2f}% | SOFR Benchmark: {sofr*100:.2f}% | Spread (10Y-3M): {macro_snap['yield_curve']['spread_10y_3m_bps']} bps")
    
    # 2. Fetch SEC EDGAR point-in-time financial statements
    print(f"[2/6] Ingesting SEC 10-K XBRL financial statements from data.sec.gov...")
    sec_client = SecEdgarClient()
    sec_data = sec_client.get_financial_history(ticker)
    if not sec_data or len(sec_data["statements"]) < 2:
        print(f"✗ Insufficient SEC 10-K history available for {ticker}.")
        return None
        
    latest_stmt = sec_data["statements"][-1]
    prior_stmt = sec_data["statements"][-2]
    print(f"      Entity: {sec_data['entity_name']} (CIK: {sec_data['cik']})")
    print(f"      Latest Fiscal Year: {latest_stmt['fiscal_year']} (Filed: {latest_stmt.get('filing_date', 'N/A')})")
    
    # 3. Fetch Live Market Data & Beta
    print(f"[3/6] Fetching market prices, shares outstanding, and beta...")
    mkt_client = MarketDataClient()
    mkt_data = mkt_client.get_market_quote(ticker)
    market_price = mkt_data["current_price"]
    shares = mkt_data["shares_outstanding"]
    market_cap = mkt_data["market_cap"]
    beta = mkt_data["beta"]
    print(f"      Current Market Price: ${market_price:,.2f} | Beta: {beta:.2f} | Market Cap: ${market_cap/1e9:,.2f}B")
    
    # 4. Compute Dynamic WACC & Multi-Stage Valuation
    print(f"[4/6] Computing Dynamic WACC, 3-Stage DCF & Residual Income Models...")
    val_engine = CfaValuationEngine()
    total_debt = latest_stmt.get("long_term_debt", 0) + latest_stmt.get("short_term_debt", 0)
    wacc_res = val_engine.compute_wacc(
        market_cap=market_cap,
        total_debt=total_debt,
        beta=beta,
        risk_free_rate=rf
    )
    wacc = wacc_res["wacc"]
    
    cfo = latest_stmt.get("operating_cash_flow", 0)
    capex = latest_stmt.get("capex", 0)
    cash = latest_stmt.get("cash_and_equivalents", 0)
    
    dcf_res = val_engine.compute_3stage_dcf(
        latest_cfo=cfo,
        latest_capex=capex,
        cash_and_equivalents=cash,
        total_debt=total_debt,
        shares_outstanding=shares,
        wacc=wacc,
        growth_stage1=growth_stage1
    )
    dcf_value = dcf_res["intrinsic_value_per_share"]
    
    book_val = latest_stmt.get("stockholders_equity", 1)
    net_inc = latest_stmt.get("net_income", 0)
    ri_res = val_engine.compute_residual_income_model(
        latest_book_value=book_val,
        latest_net_income=net_inc,
        cost_of_equity=wacc_res["cost_of_equity"],
        shares_outstanding=shares
    )
    ri_value = ri_res["intrinsic_value_per_share"]
    
    # 5. DuPont 5-Way & Competitor Benchmarking
    print(f"[5/6] Running DuPont 5-Way Decomposition & Industry Peer Benchmarks...")
    bench_engine = IndustryBenchmarkEngine()
    ratios = bench_engine.compute_cfa_ratios(latest_stmt)
    peer_comp = bench_engine.run_competitor_comparison(ticker)
    
    # 6. CAPM & SML Evaluation
    print(f"[6/6] Evaluating CAPM, Jensen's Alpha & Security Market Line Position...")
    capm_model = CapmSmlModel(risk_free_rate=rf, equity_risk_premium=0.050)
    expected_ret_est = max(0.05, 0.12 * (1.0 + (growth_stage1 - 0.08)))
    sml_res = capm_model.evaluate_security(ticker, beta=beta, realized_return_estimate=expected_ret_est)
    
    # Forensic Checks
    forensic = ForensicAccountingEngine()
    f_score_res = forensic.compute_piotroski_f_score(latest_stmt, prior_stmt)
    m_score_res = forensic.compute_beneish_m_score(latest_stmt, prior_stmt)
    sloan_res = forensic.compute_sloan_accruals(latest_stmt)
    
    margin_of_safety_pct = ((dcf_value - market_price) / max(dcf_value, 0.01)) * 100.0 if dcf_value > 0 else -100.0
    
    if margin_of_safety_pct >= 20.0 and f_score_res["piotroski_f_score"] >= 6:
        recommendation = "STRONG VALUE BUY (High Margin of Safety + Solid Quality)"
    elif margin_of_safety_pct >= 5.0 and f_score_res["piotroski_f_score"] >= 5:
        recommendation = "MODERATE BUY (Fair Value with Safety Buffer)"
    elif margin_of_safety_pct < -20.0:
        recommendation = "OVERVALUED / SELL (Trading at Steep Premium)"
    else:
        recommendation = "HOLD / FAIRLY VALUED"

    # Save to SQLite Database
    db_conn = init_valuation_db()
    save_company_valuation(db_conn, {
        "ticker": ticker,
        "cik": sec_data["cik"],
        "entity_name": sec_data["entity_name"],
        "sector": mkt_data["sector"],
        "industry": mkt_data["industry"],
        "market_price": market_price,
        "dcf_value": dcf_value,
        "residual_income_value": ri_value,
        "margin_of_safety_pct": round(margin_of_safety_pct, 2),
        "wacc": wacc,
        "piotroski_f_score": f_score_res["piotroski_f_score"],
        "beneish_m_score": m_score_res["beneish_m_score"],
        "sloan_accrual_ratio": sloan_res["sloan_accrual_ratio"],
        "recommendation": recommendation
    })
    
    # ==================== PRESENT EXECUTIVE MEMORANDUM ====================
    print("\n" + "=" * 85)
    print(f"🏛️  CFA INSTITUTIONAL EQUITY VALUATION REPORT: {ticker} ({sec_data['entity_name']})")
    print("=" * 85)
    
    summary_table = [
        ["Current Market Price", f"${market_price:,.2f}"],
        ["3-Stage DCF Intrinsic Value", f"${dcf_value:,.2f}"],
        ["Residual Income (EVA) Value", f"${ri_value:,.2f}"],
        ["Margin of Safety (%)", f"{margin_of_safety_pct:+.2f}%"],
        ["Dynamic WACC", f"{wacc*100:.2f}% (Cost of Equity: {wacc_res['cost_of_equity']*100:.2f}%)"],
        ["CAPM Required Return", f"{sml_res['capm_required_return_pct']:.2f}% | Jensen's Alpha: {sml_res['jensen_alpha_pct']:+}%"],
        ["SML Verdict", sml_res["sml_verdict"]],
        ["Piotroski F-Score (0-9)", f"{f_score_res['piotroski_f_score']}/9 ({f_score_res['rating']})"],
        ["Beneish M-Score (Manip. Risk)", f"{m_score_res['beneish_m_score']:.2f} ({m_score_res['manipulation_risk']})"],
        ["Sloan Accruals (% of Assets)", f"{sloan_res['sloan_accrual_ratio']:+.2f}% ({sloan_res['earnings_quality']})"],
        ["Macro Yield Curve Status", curve_regime],
        ["Final Valuation Stance", recommendation]
    ]
    print(tabulate(summary_table, headers=["Valuation Metric", "Value / Assessment"], tablefmt="fancy_grid"))
    
    # DuPont 5-Way Table
    print("\n🔬 DuPont 5-Way ROE Decomposition:")
    dp = ratios["dupont_5way"]
    dupont_table = [
        ["Tax Burden (NI / EBT)", f"{dp['tax_burden']:.3f}"],
        ["Interest Burden (EBT / EBIT)", f"{dp['interest_burden']:.3f}"],
        ["EBIT Operating Margin", f"{dp['ebit_margin']:.2f}%"],
        ["Asset Turnover (Rev / Assets)", f"{dp['asset_turnover']:.3f}x"],
        ["Financial Leverage (Assets / Equity)", f"{dp['financial_leverage']:.2f}x"],
        ["Calculated Return on Equity (ROE)", f"{dp['roe_pct']:.2f}%"]
    ]
    print(tabulate(dupont_table, headers=["DuPont Component", "Ratio"], tablefmt="simple"))
    
    # Industry Peer Comps Table
    if peer_comp and "peer_data" in peer_comp:
        print("\n👥 Industry Competitor Benchmark Comparison:")
        comp_rows = []
        for p in peer_comp["peer_data"]:
            comp_rows.append([
                p["ticker"],
                f"{p['operating_margin']:.1f}%",
                f"{p['roic']:.1f}%",
                f"{p['roe']:.1f}%",
                f"{p['debt_to_equity']:.2f}x",
                f"{p['ccc_days']:.0f} days"
            ])
        comp_rows.append([
            "INDUSTRY MEDIAN",
            f"{peer_comp['industry_medians']['operating_margin']:.1f}%",
            f"{peer_comp['industry_medians']['roic']:.1f}%",
            f"{peer_comp['industry_medians']['roe']:.1f}%",
            f"{peer_comp['industry_medians']['debt_to_equity']:.2f}x",
            "-"
        ])
        print(tabulate(comp_rows, headers=["Ticker", "Op Margin", "ROIC", "ROE", "Debt/Equity", "Cash Conv Cycle"], tablefmt="fancy_grid"))
        
    # Sensitivity Table
    print("\n📈 DCF Sensitivity Matrix (Intrinsic Value vs. WACC and Perpetual Growth):")
    sens = val_engine.generate_sensitivity_matrix(
        base_cfo=cfo,
        base_capex=capex,
        cash=cash,
        debt=total_debt,
        shares=shares,
        base_wacc=wacc,
        growth_rate=growth_stage1
    )
    headers = [f"g={g:.1f}%" for g in sens["growth_axis"]]
    sens_rows = [[f"WACC={sens['wacc_axis'][i]:.2f}%"] + [f"${val:,.2f}" if val > 0 else "N/A" for val in sens["matrix"][i]] for i in range(len(sens["wacc_axis"]))]
    print(tabulate(sens_rows, headers=["WACC \\ g"] + headers, tablefmt="simple"))

    # Auto-generate and save Linked Excel Financial Model
    reports_dir = Path(__file__).resolve().parent.parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    excel_path = reports_dir / f"{ticker}_Valuation_Model.xlsx"
    
    exporter = ExcelModelExporter()
    wb_bytes = exporter.generate_valuation_workbook(
        ticker=ticker,
        company_name=sec_data["entity_name"],
        current_price=market_price,
        shares_outstanding=shares,
        beta=beta,
        risk_free_rate=rf,
        wacc=wacc,
        cost_of_equity=wacc_res["cost_of_equity"],
        growth_stage1=growth_stage1,
        latest_stmt=latest_stmt,
        historical_stmts=sec_data["statements"],
        ratios=ratios,
        forensic={"f_score": f_score_res["piotroski_f_score"], "m_score": m_score_res["beneish_m_score"], "sloan_accruals": sloan_res["sloan_accrual_ratio"]}
    )
    with open(excel_path, "wb") as f:
        f.write(wb_bytes.read())
    print(f"\n📊 Linked 3-Statement & DCF Excel Model exported to: {excel_path.relative_to(Path(__file__).resolve().parent.parent)}")
    print("=" * 85)
    return dcf_value

def main():
    target_ticker = sys.argv[1] if len(sys.argv) > 1 else "MSFT"
    run_valuation_for_ticker(target_ticker)

if __name__ == "__main__":
    main()
