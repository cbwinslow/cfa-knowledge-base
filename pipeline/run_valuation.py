#!/usr/bin/env python3
"""
CFA Fundamental Valuation & Forensic Screener CLI
Runs end-to-end SEC 10-K ingestion, DCF modeling, Residual Income, and forensic accounting ratings.
"""

import sys
import os
from pathlib import Path
from tabulate import tabulate

from sec_edgar_client import SecEdgarClient
from market_data import MarketDataClient
from cfa_valuation_engine import CfaValuationEngine
from forensic_accounting import ForensicAccountingEngine
from db_storage import init_valuation_db, save_company_valuation

def run_valuation_for_ticker(ticker: str, growth_stage1: float = 0.08):
    ticker = ticker.upper()
    print("=" * 75)
    print(f"📊 INITIATING CFA VALUATION PIPELINE FOR: {ticker}")
    print("=" * 75)
    
    # 1. Fetch SEC EDGAR point-in-time financial statements
    sec_client = SecEdgarClient()
    print(f"[1/5] Fetching SEC 10-K XBRL financial statements from data.sec.gov...")
    sec_data = sec_client.get_financial_history(ticker)
    if not sec_data or len(sec_data["statements"]) < 2:
        print(f"✗ Insufficient SEC 10-K history available for {ticker}.")
        return None
        
    latest_stmt = sec_data["statements"][-1]
    prior_stmt = sec_data["statements"][-2]
    print(f"      Entity: {sec_data['entity_name']} (CIK: {sec_data['cik']})")
    print(f"      Latest 10-K Fiscal Year: {latest_stmt['fiscal_year']} (Filed: {latest_stmt.get('filing_date', 'N/A')})")
    
    # 2. Fetch Live Market Data & Treasury Yield
    print(f"[2/5] Fetching market prices, beta, and 10-Yr US Treasury yield...")
    mkt_client = MarketDataClient()
    mkt_data = mkt_client.get_market_quote(ticker)
    market_price = mkt_data["current_price"]
    shares = mkt_data["shares_outstanding"]
    market_cap = mkt_data["market_cap"]
    beta = mkt_data["beta"]
    rf = mkt_data["risk_free_rate"]
    print(f"      Current Market Price: ${market_price:,.2f} | Beta: {beta:.2f} | 10-Yr Treasury: {rf*100:.2f}%")
    
    # 3. Compute Dynamic WACC
    print(f"[3/5] Computing Dynamic WACC via CAPM & Cost of Debt...")
    val_engine = CfaValuationEngine()
    total_debt = latest_stmt.get("long_term_debt", 0) + latest_stmt.get("short_term_debt", 0)
    wacc_res = val_engine.compute_wacc(
        market_cap=market_cap,
        total_debt=total_debt,
        beta=beta,
        risk_free_rate=rf
    )
    wacc = wacc_res["wacc"]
    print(f"      Calculated WACC: {wacc*100:.2f}% (Cost of Equity: {wacc_res['cost_of_equity']*100:.2f}%)")
    
    # 4. Multi-Stage DCF & Residual Income Valuation
    print(f"[4/5] Computing 3-Stage DCF & Residual Income Valuation Models...")
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
    
    # 5. Forensic Accounting & Earnings Quality
    print(f"[5/5] Running Forensic Accounting Audit (Piotroski F & Beneish M)...")
    forensic = ForensicAccountingEngine()
    f_score_res = forensic.compute_piotroski_f_score(latest_stmt, prior_stmt)
    m_score_res = forensic.compute_beneish_m_score(latest_stmt, prior_stmt)
    sloan_res = forensic.compute_sloan_accruals(latest_stmt)
    
    # Margin of Safety calculation
    margin_of_safety_pct = ((dcf_value - market_price) / max(dcf_value, 0.01)) * 100.0 if dcf_value > 0 else -100.0
    
    # Recommendation Logic
    if margin_of_safety_pct >= 20.0 and f_score_res["piotroski_f_score"] >= 6:
        recommendation = "STRONG VALUE BUY (High Margin of Safety + Solid Quality)"
    elif margin_of_safety_pct >= 5.0 and f_score_res["piotroski_f_score"] >= 5:
        recommendation = "MODERATE BUY (Fair Value with Safety Buffer)"
    elif margin_of_safety_pct < -20.0:
        recommendation = "OVERVALUED / SELL (Trading at Steep Premium)"
    else:
        recommendation = "HOLD / FAIRLY VALUED"

    # Save to SQLite
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
    
    # ==================== DISPLAY EXECUTIVE REPORT ====================
    print("\n" + "=" * 75)
    print(f"🏛️  CFA INSTITUTIONAL VALUATION MEMO: {ticker} ({sec_data['entity_name']})")
    print("=" * 75)
    
    summary_table = [
        ["Current Market Price", f"${market_price:,.2f}"],
        ["3-Stage DCF Intrinsic Value", f"${dcf_value:,.2f}"],
        ["Residual Income Intrinsic Value", f"${ri_value:,.2f}"],
        ["Margin of Safety (%)", f"{margin_of_safety_pct:+.2f}%"],
        ["Piotroski F-Score (0-9)", f"{f_score_res['piotroski_f_score']}/9 ({f_score_res['rating']})"],
        ["Beneish M-Score (Manip. Risk)", f"{m_score_res['beneish_m_score']:.2f} ({m_score_res['manipulation_risk']})"],
        ["Sloan Accruals (% of Assets)", f"{sloan_res['sloan_accrual_ratio']:+.2f}% ({sloan_res['earnings_quality']})"],
        ["Final Valuation Stance", recommendation]
    ]
    print(tabulate(summary_table, headers=["Valuation Metric", "Value / Assessment"], tablefmt="fancy_grid"))
    
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
    print("=" * 75)
    return dcf_value

def main():
    target_ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    run_valuation_for_ticker(target_ticker)

if __name__ == "__main__":
    main()
