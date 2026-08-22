"""
Comprehensive Unit & Boundary Tests for Valuation and Forensic Accounting
"""

import pytest
from cfa_quant.valuation import CfaValuationEngine, ForensicAccountingEngine, CapmSmlModel

def test_3stage_dcf_model_convergence():
    engine = CfaValuationEngine()
    
    cfo = 100000000.0
    capex = 20000000.0  # FCF = 80M
    cash = 50000000.0
    debt = 100000000.0
    shares = 10000000
    wacc = 0.09
    g1 = 0.12
    
    res = engine.compute_3stage_dcf(cfo, capex, cash, debt, shares, wacc, growth_stage1=g1)
    
    assert res["intrinsic_value_per_share"] > 0.0, "DCF value must be positive"
    assert res["enterprise_value"] > res["pv_terminal_value"], "EV must exceed terminal value PV"
    assert len(res["projected_cash_flows"]) == 7, "Default 3 + 4 = 7 forecast years"

def test_residual_income_model():
    engine = CfaValuationEngine()
    book_val = 500000000.0
    net_income = 80000000.0
    cost_of_equity = 0.10
    shares = 10000000
    
    ri_res = engine.compute_residual_income_model(book_val, net_income, cost_of_equity, shares, forecast_roe=0.15)
    
    assert ri_res["total_equity_value"] > book_val, "With ROE (15%) > cost of equity (10%), total equity value must exceed book value"
    assert ri_res["intrinsic_value_per_share"] > (book_val / shares), "Intrinsic value must exceed book value per share"

def test_piotroski_f_score_nine_criteria():
    forensic = ForensicAccountingEngine()
    
    latest = {
        "net_income": 1000000,
        "operating_cash_flow": 1200000,
        "total_assets": 10000000,
        "long_term_debt": 1000000,
        "current_assets": 4000000,
        "current_liabilities": 2000000,
        "gross_profit": 3000000,
        "total_revenue": 8000000,
        "shares_outstanding": 1000000
    }
    prior = {
        "net_income": 800000,
        "operating_cash_flow": 900000,
        "total_assets": 9500000,
        "long_term_debt": 1500000,
        "current_assets": 3500000,
        "current_liabilities": 2000000,
        "gross_profit": 2500000,
        "total_revenue": 7000000,
        "shares_outstanding": 1000000
    }
    
    score_res = forensic.compute_piotroski_f_score(latest, prior)
    assert score_res["piotroski_f_score"] >= 7, f"Expected strong F-Score >= 7, got {score_res['piotroski_f_score']}"

def test_beneish_m_score_manipulation_threshold():
    forensic = ForensicAccountingEngine()
    
    latest = {"total_revenue": 10000000, "gross_profit": 4000000, "total_assets": 20000000, "operating_cash_flow": 2500000, "net_income": 1500000, "receivables": 1200000, "cogs": 6000000, "ppe": 8000000, "depreciation": 500000, "sg_and_a": 1000000, "long_term_debt": 3000000, "current_liabilities": 2000000}
    prior = {"total_revenue": 9000000, "gross_profit": 3600000, "total_assets": 19000000, "operating_cash_flow": 2200000, "net_income": 1400000, "receivables": 1100000, "cogs": 5400000, "ppe": 7800000, "depreciation": 480000, "sg_and_a": 950000, "long_term_debt": 3100000, "current_liabilities": 1900000}
    
    m_res = forensic.compute_beneish_m_score(latest, prior)
    assert m_res["beneish_m_score"] < -1.78, f"Expected clean Beneish M-Score < -1.78, got {m_res['beneish_m_score']}"
