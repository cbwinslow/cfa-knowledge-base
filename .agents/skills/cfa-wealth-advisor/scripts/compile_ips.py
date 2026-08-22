#!/usr/bin/env python3
"""
CFA Level III Investment Policy Statement (IPS) Compiler Script
Takes raw client profile JSON/YAML, computes quantitative objectives & TTLLU constraints,
and outputs a complete, audit-ready IPS.
"""

import sys
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any

# Ensure project root in python path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from cfa_quant.ips_generator import IpsGeneratorEngine, ClientProfile
from cfa_quant.tax_legal_engine import TaxLegalOptimizationEngine, AccountBalances

def compile_ips_from_file(input_json_path: Path) -> str:
    with open(input_json_path, "r") as f:
        data = json.load(f)
        
    p = data.get("client_profile", data)
    
    profile = ClientProfile(
        client_names=p["client_names"],
        ages=p["ages"],
        residence_jurisdiction=p.get("residence", "United States"),
        total_investable_assets=float(p["total_investable_assets"]),
        annual_spending_needs=float(p["annual_spending_needs"]),
        expected_inflation_rate=float(p.get("expected_inflation_rate", 0.025)),
        effective_income_tax_rate=float(p.get("effective_income_tax_rate", 0.30)),
        capital_gains_tax_rate=float(p.get("capital_gains_tax_rate", 0.20)),
        bequest_legacy_goal=float(p.get("bequest_legacy_goal", 0.0)),
        human_capital_value=float(p.get("human_capital_value", 0.0)),
        human_capital_type=p.get("human_capital_type", "bond_like"),
        risk_willingness=p.get("risk_willingness", "Moderate"),
        time_horizon_stages=p.get("time_horizon_stages", []),
        liquidity_buffer_months=p.get("liquidity_requirements", {}).get("emergency_cash_months", 12),
        legal_structures=p.get("legal_and_tax_structures", []),
        unique_mandates=p.get("unique_mandates", [])
    )
    
    engine = IpsGeneratorEngine()
    ips_md = engine.generate_full_ips_document(profile)
    return ips_md

def main():
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
    else:
        file_path = Path(__file__).resolve().parent.parent / "examples" / "client_case_entrepreneur.json"
        
    if not file_path.exists():
        print(f"Error: File {file_path} not found.")
        sys.exit(1)
        
    doc = compile_ips_from_file(file_path)
    print(doc)

if __name__ == "__main__":
    main()
