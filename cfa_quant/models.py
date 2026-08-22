"""
CFA Quantitative Suite - Core Domain Models & Schemas
Typed, portable data contracts ensuring seamless interoperability across CLI, Web, and Excel exporters.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class FinancialStatementRecord:
    fiscal_year: int
    filing_date: str
    revenue: float
    cost_of_revenue: float
    gross_profit: float
    operating_income: float  # EBIT
    net_income: float
    operating_cash_flow: float  # CFO
    capex: float
    free_cash_flow: float
    total_assets: float
    total_debt: float
    stockholders_equity: float
    cash_and_equivalents: float
    accounts_receivable: float
    inventory: float

@dataclass
class MacroeconomicSnapshot:
    yield_10y_treasury: float
    sofr_benchmark_rate: float
    fed_funds_rate: float
    breakeven_inflation_10y: float
    high_yield_credit_spread: float
    yield_curve_spread_10y_3m_bps: float
    is_yield_curve_inverted: bool
    regime_status: str

@dataclass
class ValuationResult:
    ticker: str
    company_name: str
    current_market_price: float
    dcf_intrinsic_value: float
    residual_income_value: float
    margin_of_safety_pct: float
    calculated_wacc: float
    cost_of_equity: float
    cost_of_debt_after_tax: float
    piotroski_f_score: int
    beneish_m_score: float
    sloan_accrual_ratio: float
    recommendation: str
    sensitivity_matrix: Dict[str, Any] = field(default_factory=dict)

@dataclass
class OpportunityCostAssessment:
    ticker: str
    market_price: float
    fcf_yield_pct: float
    risk_free_rate_pct: float
    equity_risk_premium_pct: float
    fcf_yield_spread_over_treasury_bps: float  # FCF Yield minus 10-Yr Treasury
    roic_pct: float
    wacc_pct: float
    economic_value_added_spread_pct: float     # ROIC minus WACC
    hurdle_rate_cleared: bool
    next_best_competitor_ticker: str
    next_best_competitor_eva_spread: float
    opportunity_cost_verdict: str

@dataclass
class PeerBenchmarkSummary:
    target_ticker: str
    sector: str
    peers: List[str]
    target_percentile_roic: float
    target_percentile_operating_margin: float
    target_percentile_fcf_yield: float
    industry_median_roic: float
    industry_median_op_margin: float
    industry_median_debt_to_equity: float
    ranking_leaderboard: List[Dict[str, Any]]
