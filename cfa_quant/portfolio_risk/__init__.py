"""
CFA Level III Portfolio Construction, SAA & Risk Analytics Package
Exports:
- ScenarioLabEngine (Multi-Portfolio Head-to-Head & Macro Stress Testing)
- MarginalAllocationEngine (Incremental Asset Addition, MCTR, %CTR Risk Donut)
- FixedIncomeLdiEngine (LDI Immunization, Key Rate Dispersion, Yield Curve Shifts)
- VolatilitySurfaceEngine (3D Implied Volatility Surface & 25-Delta Skew)
"""

from cfa_quant.scenario_lab import ScenarioLabEngine
from cfa_quant.marginal_allocation import MarginalAllocationEngine
from cfa_quant.fixed_income_ldi import FixedIncomeLdiEngine
from cfa_quant.volatility_surface import VolatilitySurfaceEngine

__all__ = [
    "ScenarioLabEngine",
    "MarginalAllocationEngine",
    "FixedIncomeLdiEngine",
    "VolatilitySurfaceEngine"
]
