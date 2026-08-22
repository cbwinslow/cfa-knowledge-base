"""
CFA Level I & II Polymorphic Valuation Package
Exports:
- BaseValuationModel (Abstract Base Class)
- ThreeStageDcfValuation (Explicit + Transition + Gordon Terminal)
- ResidualIncomeValuation (Book Value + PV of Residual Income Alpha)
- DividendDiscountModelValuation (Two-Stage DDM)
- MarketMultiplesValuation (Peer Relative EV/EBITDA & P/E)
- UnifiedValuationSuite (Polymorphic Ensemble & Consensus Triangulation)
- CfaValuationEngine (Legacy Multi-Engine Wrapper)
- ForensicAccountingEngine (Piotroski F-Score, Beneish M-Score, Sloan Accruals)
- CapmSmlModel (Security Market Line, Jensen's Alpha)
- IndustryBenchmarkEngine (Competitor Comps & DuPont 5-Way)
- ExcelModelExporter (Linked 3-Statement & DCF Workbook Generator)
"""

from cfa_quant.valuation.polymorphic_valuation import (
    BaseValuationModel,
    ValuationOutput,
    ThreeStageDcfValuation,
    ResidualIncomeValuation,
    DividendDiscountModelValuation,
    MarketMultiplesValuation,
    UnifiedValuationSuite
)
from pipeline.cfa_valuation_engine import CfaValuationEngine
from pipeline.forensic_accounting import ForensicAccountingEngine
from pipeline.capm_sml_model import CapmSmlModel
from pipeline.industry_benchmarks import IndustryBenchmarkEngine
from cfa_quant.excel_exporter import ExcelModelExporter

__all__ = [
    "BaseValuationModel",
    "ValuationOutput",
    "ThreeStageDcfValuation",
    "ResidualIncomeValuation",
    "DividendDiscountModelValuation",
    "MarketMultiplesValuation",
    "UnifiedValuationSuite",
    "CfaValuationEngine",
    "ForensicAccountingEngine",
    "CapmSmlModel",
    "IndustryBenchmarkEngine",
    "ExcelModelExporter"
]
