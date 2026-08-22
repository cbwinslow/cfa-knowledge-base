"""
CFA Quantitative Suite - Institutional Equity Research & Wealth Management Platform
Version: 2.0.0
Author: CFA Quantitative Team
License: Proprietary / Fiduciary Standard

Master Top-Level Package Exports
"""

__version__ = "2.0.0"

# 1. Multi-Asset Instruments & Portfolio Engine (Polymorphic InvestmentInstrument hierarchy)
from cfa_quant.instruments import (
    InvestmentInstrument,
    AssetClass,
    FixedCouponBond,
    ZeroCouponBond,
    InflationLinkedBond,
    MunicipalBond,
    MortgageBackedSecurity,
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

# 2. Valuation & Financial Modeling (Polymorphic BaseValuationModel hierarchy)
from cfa_quant.valuation import (
    BaseValuationModel,
    ValuationOutput,
    ThreeStageDcfValuation,
    ResidualIncomeValuation,
    DividendDiscountModelValuation,
    MarketMultiplesValuation,
    UnifiedValuationSuite,
    CfaValuationEngine,
    ForensicAccountingEngine,
    CapmSmlModel,
    IndustryBenchmarkEngine,
    ExcelModelExporter
)

# 3. Portfolio Construction, Asset Allocation, GIPS, Multi-Factor Risk & Rebalancing
from cfa_quant.portfolio_risk import (
    FactorRiskModelEngine,
    ActiveRiskDecomposition,
    FactorExposure,
    PortfolioRebalancingEngine,
    RebalancingBlotter,
    TradeOrder,
    BlackLittermanEngine,
    GipsCompositeEngine,
    ScenarioLabEngine,
    MarginalAllocationEngine,
    PerformanceAttributionEngine,
    BrinsonAttributionReport,
    CampisiFixedIncomeAttributionReport,
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

# 5. Data, Security Master, Custodian Gateway, News Wire & Transaction Warehouse
from cfa_quant.data import (
    SecurityMaster,
    TransactionLedger,
    CustodianIngestionGateway,
    NewsWireEngine,
    NewsWebSocketServer,
    AnalyticsStore,
    TaxLot,
    RealizedGainRecord,
    DatabaseAdapter,
    DuckDbAdapter,
    SQLiteAdapter,
    ClickHouseAdapter,
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
    "MunicipalBond",
    "MortgageBackedSecurity",
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
    # Polymorphic Valuation
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
    "ExcelModelExporter",
    # Portfolio Risk, Multi-Factor, GIPS & Rebalancing
    "FactorRiskModelEngine",
    "ActiveRiskDecomposition",
    "FactorExposure",
    "PortfolioRebalancingEngine",
    "RebalancingBlotter",
    "TradeOrder",
    "BlackLittermanEngine",
    "GipsCompositeEngine",
    "ScenarioLabEngine",
    "MarginalAllocationEngine",
    "PerformanceAttributionEngine",
    "BrinsonAttributionReport",
    "CampisiFixedIncomeAttributionReport",
    "FixedIncomeLdiEngine",
    "VolatilitySurfaceEngine",
    # Wealth Advisory
    "LifeCyclePortfolioEngine",
    "LifeCycleClient",
    "IpsGeneratorEngine",
    "ClientProfile",
    "TaxLegalOptimizationEngine",
    "AccountBalances",
    # Data & Warehouse
    "SecurityMaster",
    "TransactionLedger",
    "CustodianIngestionGateway",
    "NewsWireEngine",
    "NewsWebSocketServer",
    "AnalyticsStore",
    "TaxLot",
    "RealizedGainRecord",
    "DatabaseAdapter",
    "DuckDbAdapter",
    "SQLiteAdapter",
    "ClickHouseAdapter",
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
