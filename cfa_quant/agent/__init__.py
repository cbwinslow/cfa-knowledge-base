"""
CFA Agentic Copilot & Hybrid RAG Package
Exports:
- CfaAgentHarness (2026-anchored tool calling and sandbox workspace)
- HybridRagEngine (FastEmbed ONNX + SQLite FTS5 RRF retrieval)
"""

from cfa_quant.agent_harness import CfaAgentHarness
from cfa_quant.rag_engine import HybridRagEngine

__all__ = [
    "CfaAgentHarness",
    "HybridRagEngine"
]
