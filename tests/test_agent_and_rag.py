"""
Unit Tests for CFA Agentic Copilot and Hybrid RAG Engine
"""

import pytest
from cfa_quant.agent import CfaAgentHarness, HybridRagEngine

def test_hybrid_rag_search():
    rag = HybridRagEngine()
    results = rag.search_hybrid("Grinold-Kroner expected equity return", top_k=3)
    
    assert len(results) > 0, "Hybrid RAG should return relevant CFA curriculum items"
    assert "topic" in results[0]
    assert "content" in results[0]

def test_copilot_intent_dispatching_and_workspace(tmp_path):
    harness = CfaAgentHarness(workspace_dir=tmp_path)
    
    # 1. Test Valuation Intent
    res_val = harness.process_chat_message("What is the valuation of MSFT?")
    assert "CfaValuationEngine" in str(res_val["tool_invoked"])
    assert "DCF" in res_val["response"]
    
    # 2. Test Portfolio Incremental Addition Intent
    res_add = harness.process_chat_message("show me how my portfolio would change if we added 500 shares of AAPL to our portfolio")
    assert "MarginalAllocationEngine" in str(res_add["tool_invoked"])
    assert "Pre- vs. Post-Allocation Metrics" in res_add["response"]
    
    # 3. Test Workspace File Write and Read
    write_msg = harness.write_workspace_file("test_memo.md", "# Test Wealth Strategy Memo")
    assert "Successfully saved" in write_msg
    
    content = harness.read_workspace_file("test_memo.md")
    assert "# Test Wealth Strategy Memo" in content
    
    files = harness.list_workspace_files()
    assert len(files) == 1
    assert files[0]["filename"] == "test_memo.md"
