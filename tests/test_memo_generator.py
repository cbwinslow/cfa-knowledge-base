"""
Unit, Invariant, and Output Validation Tests for Investment Committee Memorandum Packager
"""

import pytest
from cfa_quant.reports.memo_generator import MemoGeneratorEngine, InvestmentCommitteeMemo

def test_memo_generator_markdown_and_html_generation():
    engine = MemoGeneratorEngine()
    memo = engine.generate_committee_memo(
        mandate_name="Global Endowment Fund Alpha",
        committee_name="Board of Trustees Investment Committee",
        author_analyst="Jane Doe, CFA",
        portfolio_aum_usd=50000000.0,
        target_benchmark="70/30 Global Growth Index",
        executive_verdict="APPROVE Strategic Allocation"
    )
    
    assert isinstance(memo, InvestmentCommitteeMemo)
    assert memo.mandate_name == "Global Endowment Fund Alpha"
    assert memo.portfolio_aum_usd == 50000000.0
    
    # 1. Test Markdown Output
    md_text = memo.to_markdown()
    assert "# 🏛️ INSTITUTIONAL INVESTMENT COMMITTEE MEMORANDUM" in md_text
    assert "Global Endowment Fund Alpha" in md_text
    assert "$50,000,000.00" in md_text
    assert "APPROVE Strategic Allocation" in md_text
    assert "Consensus Mean Fair Value" in md_text
    assert "Black-Litterman Strategic & Tactical Asset Allocation" in md_text
    assert "Barra / Fama-French Multi-Factor Active Risk Decomposition" in md_text
    assert "Tax-Aware Rebalancing Schedule" in md_text
    assert "GIPS Composite Annual Presentation" in md_text
    assert "Walk-Forward Backtesting Risk-Adjusted Analytics" in md_text
    assert "Fiduciary & Compliance Sign-Off" in md_text
    
    # 2. Test HTML Output
    html_text = memo.to_html()
    assert "<!DOCTYPE html>" in html_text
    assert "<title>Investment Committee Memo - Global Endowment Fund Alpha</title>" in html_text
    assert "CONFIDENTIAL - INVESTMENT COMMITTEE USE ONLY" in html_text
    assert "<table>" in html_text or "th {" in html_text

def test_memo_generator_custom_verdict_and_fallback():
    engine = MemoGeneratorEngine()
    memo_custom = engine.generate_committee_memo(executive_verdict="REJECT Overweight tilt due to elevated macro volatility")
    assert "REJECT Overweight tilt" in memo_custom.executive_verdict
    assert "REJECT Overweight tilt" in memo_custom.to_markdown()
