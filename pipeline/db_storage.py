#!/usr/bin/env python3
"""
Valuation & Financial Statement Database Storage
Persists point-in-time SEC statement facts, DCF intrinsic values, and forensic scores.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cfa_valuation_store.sqlite"

def init_valuation_db(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Companies Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        ticker TEXT PRIMARY KEY,
        cik TEXT,
        name TEXT,
        sector TEXT,
        industry TEXT,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Point-in-time Financial Statements Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_statements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT,
        fiscal_year INTEGER,
        filing_date TEXT,
        revenue REAL,
        operating_income REAL,
        net_income REAL,
        operating_cash_flow REAL,
        capex REAL,
        total_assets REAL,
        total_debt REAL,
        stockholders_equity REAL,
        raw_json TEXT,
        FOREIGN KEY (ticker) REFERENCES companies(ticker),
        UNIQUE(ticker, fiscal_year)
    );
    """)
    
    # Valuations & Forensic Scores Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS company_valuations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT,
        valuation_date TEXT,
        market_price REAL,
        dcf_intrinsic_value REAL,
        margin_of_safety_pct REAL,
        residual_income_value REAL,
        wacc REAL,
        piotroski_f_score INTEGER,
        beneish_m_score REAL,
        sloan_accrual_ratio REAL,
        recommendation TEXT,
        FOREIGN KEY (ticker) REFERENCES companies(ticker)
    );
    """)
    
    conn.commit()
    return conn

def save_company_valuation(conn: sqlite3.Connection, val_record: Dict[str, Any]):
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO companies (ticker, cik, name, sector, industry)
    VALUES (?, ?, ?, ?, ?)
    """, (
        val_record["ticker"],
        val_record.get("cik", ""),
        val_record.get("entity_name", val_record["ticker"]),
        val_record.get("sector", "General"),
        val_record.get("industry", "General")
    ))
    
    cursor.execute("""
    INSERT INTO company_valuations (
        ticker, valuation_date, market_price, dcf_intrinsic_value,
        margin_of_safety_pct, residual_income_value, wacc,
        piotroski_f_score, beneish_m_score, sloan_accrual_ratio, recommendation
    )
    VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        val_record["ticker"],
        val_record["market_price"],
        val_record["dcf_value"],
        val_record["margin_of_safety_pct"],
        val_record.get("residual_income_value", 0.0),
        val_record["wacc"],
        val_record["piotroski_f_score"],
        val_record["beneish_m_score"],
        val_record["sloan_accrual_ratio"],
        val_record["recommendation"]
    ))
    conn.commit()
