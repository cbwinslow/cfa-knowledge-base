"""
CFA Quantitative Suite - Institutional Equity Research & Wealth Management Platform
Version: 2.0.0
Author: CFA Quantitative Team
License: Proprietary / Fiduciary Standard

Master Top-Level Package Exports
"""

__version__ = "2.0.0"

# 1. Multi-Asset Instruments & Portfolio Engine
from cfa_quant.instruments import (
    InvestmentInstrument,
    AssetClass,
    FixedCouponBond,
    ZeroCouponBond,
    InflationLinkedBond,
    PublicEquityStock,
    RealEstateAsset,
    PrivateEquityHolding,
    InterestRateSwap,
    ForexForward,
    EquityIndexFutures,
    OptionsContract,
    MarketMicrostructureEngine,
    OrderBookSnapshot,
    OrderBookLevel,
    ImplementationShortfallResult,
    UnifiedPortfolio
)

# 2. Valuation & Financial Modeling
from cfa_quant.valuation import (
    CfaValuationEngine,
    ForensicAccountingEngine,
    CapmSmlModel,
    IndustryBenchmarkEngine,
    ExcelModelExporter
)

# 3. Portfolio Construction & Macro Risk
from cfa_quant.portfolio_risk import (
    ScenarioLabEngine,
    MarginalAllocationEngine,
    FixedIncomeLdiEngine,
    VolatilitySurfaceEngine
)

# 4. Wealth Advisory & Life-Cycle Management
from cfa_quant.wealth_advisory import (
    LifeCyclePortfolioEngine,
    LifeCycleClient,
    IpsGeneratorEngine,
    ClientProfile,
    TaxLegalOptimizationEngine,
    AccountBalances
)

# 5. Data & Warehouse Storage
from cfa_quant.data import (
    CentralDataHopper,
    MacroEngine,
    SecEdgarClient,
    MarketDataClient,
    DuckDbMacroStore
)

# 6. Autonomous Copilot & Hybrid RAG
from cfa_quant.agent import (
    CfaAgentHarness,
    HybridRagEngine
)

# 7. Visualizations
from cfa_quant.visual import (
    PortfolioVisualizer,
    FinancialChartEngine
)

__all__ = [
    "__version__",
    # Instruments & Portfolio
    "InvestmentInstrument",
    "AssetClass",
    "FixedCouponBond",
    "ZeroCouponBond",
    "InflationLinkedBond",
    "PublicEquityStock",
    "RealEstateAsset",
    "PrivateEquityHolding",
    "InterestRateSwap",
    "ForexForward",
    "EquityIndexFutures",
    "OptionsContract",
    "MarketMicrostructureEngine",
    "OrderBookSnapshot",
    "OrderBookLevel",
    "ImplementationShortfallResult",
    "UnifiedPortfolio",
    # Valuation
    "CfaValuationEngine",
    "ForensicAccountingEngine",
    "CapmSmlModel",
    "IndustryBenchmarkEngine",
    "ExcelModelExporter",
    # Portfolio Risk
    "ScenarioLabEngine",
    "MarginalAllocationEngine",
    "FixedIncomeLdiEngine",
    "VolatilitySurfaceEngine",
    # Wealth Advisory
    "LifeCyclePortfolioEngine",
    "LifeCycleClient",
    "IpsGeneratorEngine",
    "ClientProfile",
    "TaxLegalOptimizationEngine",
    "AccountBalances",
    # Data
    "CentralDataHopper",
    "MacroEngine",
    "SecEdgarClient",
    "MarketDataClient",
    "DuckDbMacroStore",
    # Agent
    "CfaAgentHarness",
    "HybridRagEngine",
    # Visual
    "PortfolioVisualizer",
    "FinancialChartEngine"
]
