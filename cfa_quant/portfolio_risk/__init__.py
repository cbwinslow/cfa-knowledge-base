"""
Portfolio Risk, Optimization & Asset Allocation Package
Exports:
- BlackLittermanEngine (Implied Equilibrium & Subjective View Blending)
- ScenarioLabEngine (Cross-Asset Macro Stress Testing)
- MarginalAllocationEngine (MCTR & Euler Capital Budgeting)
- PerformanceAttributionEngine (Brinson-Fachler, Campisi & Carino Linking)
- BrinsonAttributionReport, CampisiFixedIncomeAttributionReport
- FixedIncomeLdiEngine (Liability-Driven Immunization)
- VolatilitySurfaceEngine (SVI & Local Volatility Modeling)
"""

from cfa_quant.portfolio_risk.black_litterman import BlackLittermanEngine
from cfa_quant.scenario_lab import ScenarioLabEngine
from cfa_quant.marginal_allocation import MarginalAllocationEngine
from cfa_quant.portfolio_risk.attribution_engine import (
    PerformanceAttributionEngine,
    BrinsonAttributionReport,
    CampisiFixedIncomeAttributionReport
)
from cfa_quant.fixed_income_ldi import FixedIncomeLdiEngine
from cfa_quant.volatility_surface import VolatilitySurfaceEngine

__all__ = [
    "BlackLittermanEngine",
    "ScenarioLabEngine",
    "MarginalAllocationEngine",
    "PerformanceAttributionEngine",
    "BrinsonAttributionReport",
    "CampisiFixedIncomeAttributionReport",
    "FixedIncomeLdiEngine",
    "VolatilitySurfaceEngine"
]
