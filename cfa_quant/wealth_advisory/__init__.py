"""
CFA Level III Private Wealth & Life-Cycle Management Package
Exports:
- LifeCyclePortfolioEngine (4-Stage Life-Cycle, Human Capital NPV, GBWM Buckets)
- IpsGeneratorEngine (Institutional IPS Generator)
- TaxLegalOptimizationEngine (Asset Location & Relocation Arbitrage)
"""

from cfa_quant.lifecycle_portfolio import LifeCyclePortfolioEngine, LifeCycleClient
from cfa_quant.ips_generator import IpsGeneratorEngine, ClientProfile
from cfa_quant.tax_legal_engine import TaxLegalOptimizationEngine, AccountBalances

__all__ = [
    "LifeCyclePortfolioEngine",
    "LifeCycleClient",
    "IpsGeneratorEngine",
    "ClientProfile",
    "TaxLegalOptimizationEngine",
    "AccountBalances"
]
