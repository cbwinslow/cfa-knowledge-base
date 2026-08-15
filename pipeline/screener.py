#!/usr/bin/env python3
"""
CFA Multi-Stock Fundamental Valuation & Margin of Safety Screener
Batches through a universe of tickers, executes full SEC 10-K DCF + Forensics,
and outputs a ranked leaderboard of undervalued opportunities.
"""

import sys
from tabulate import tabulate
from run_valuation import run_valuation_for_ticker
from db_storage import init_valuation_db

DEFAULT_UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JNJ", "JPM", "XOM", "PG"]

def run_screener(tickers=None):
    tickers = tickers or DEFAULT_UNIVERSE
    print("=" * 85)
    print(f"🚀 RUNNING CFA FUNDAMENTAL VALUE SCREENER ON {len(tickers)} COMPANIES")
    print("=" * 85)
    
    conn = init_valuation_db()
    
    for t in tickers:
        try:
            run_valuation_for_ticker(t)
        except Exception as e:
            print(f"Error evaluating {t}: {e}")
            
    cursor = conn.cursor()
    cursor.execute("""
    SELECT ticker, market_price, dcf_intrinsic_value, margin_of_safety_pct,
           piotroski_f_score, beneish_m_score, sloan_accrual_ratio, recommendation
    FROM company_valuations
    ORDER BY margin_of_safety_pct DESC;
    """)
    rows = cursor.fetchall()
    
    table_data = []
    for r in rows:
        table_data.append([
            r[0],
            f"${r[1]:,.2f}",
            f"${r[2]:,.2f}",
            f"{r[3]:+.2f}%",
            f"{r[4]}/9",
            f"{r[5]:.2f}",
            f"{r[6]:+.2f}%",
            r[7].split(" ")[0] + " " + r[7].split(" ")[1] if len(r[7].split(" ")) > 1 else r[7]
        ])
        
    print("\n" + "=" * 85)
    print("🏆  CFA QUANTITATIVE VALUE & SAFETY LEADERBOARD")
    print("=" * 85)
    print(tabulate(
        table_data,
        headers=["Ticker", "Price", "DCF Intrinsic", "Margin of Safety", "Piotroski", "Beneish M", "Sloan Accrual", "Stance"],
        tablefmt="fancy_grid"
    ))
    print("=" * 85)

if __name__ == "__main__":
    tickers_arg = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    run_screener(tickers_arg)
