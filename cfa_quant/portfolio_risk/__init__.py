"""
CFA Level III Portfolio Construction, SAA & Performance Attribution Package
Exports:
- ScenarioLabEngine (Multi-Portfolio Head-to-Head & Macro Stress Testing)
- MarginalAllocationEngine (Incremental Asset Addition, MCTR, %CTR Risk Donut)
- PerformanceAttributionEngine (Brinson-Fachler Equity & Campisi Fixed Income Attribution)
- FixedIncomeLdiEngine (LDI Immunization, Key Rate Dispersion, Yield Curve Shifts)
- VolatilitySurfaceEngine (3D Implied Volatility Surface & 25-Delta Skew)
"""

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
    "ScenarioLabEngine",
    "MarginalAllocationEngine",
    "PerformanceAttributionEngine",
    "BrinsonAttributionReport",
    "CampisiFixedIncomeAttributionReport",
    "FixedIncomeLdiEngine",
    "VolatilitySurfaceEngine"
]
