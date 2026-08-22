"""
Portfolio Risk, Optimization, Asset Allocation & GIPS Reporting Package
Exports:
- BlackLittermanEngine (Implied Equilibrium & Subjective View Blending)
- GipsCompositeEngine (GIPS Compliance, TWRR, Modified Dietz & Composite Dispersion)
- ScenarioLabEngine (Cross-Asset Macro Stress Testing)
- MarginalAllocationEngine (MCTR & Euler Capital Budgeting)
- PerformanceAttributionEngine (Brinson-Fachler, Campisi & Carino Linking)
- BrinsonAttributionReport, CampisiFixedIncomeAttributionReport
- FixedIncomeLdiEngine (Liability-Driven Immunization)
- VolatilitySurfaceEngine (SVI & Local Volatility Modeling)
"""

from cfa_quant.portfolio_risk.black_litterman import BlackLittermanEngine
from cfa_quant.portfolio_risk.gips_composites import GipsCompositeEngine
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
    "GipsCompositeEngine",
    "ScenarioLabEngine",
    "MarginalAllocationEngine",
    "PerformanceAttributionEngine",
    "BrinsonAttributionReport",
    "CampisiFixedIncomeAttributionReport",
    "FixedIncomeLdiEngine",
    "VolatilitySurfaceEngine"
]
