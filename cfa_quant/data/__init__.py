"""
Centralized Data Ingestion, Security Master & News Wire Package
Exports:
- SecurityMaster (Multi-Identifier CUSIP/ISIN/FIGI/Ticker Resolution)
- TransactionLedger (High-Scale DuckDB Ledger & HIFO Tax Lot Accounting)
- CustodianIngestionGateway (Universal Schwab, Fidelity, IBKR, Pershing, OFX, FIX Parser)
- NewsWireEngine (Bloomberg-Style Financial News Wire & Vector Engine)
- NewsWebSocketServer (Real-Time Async Streaming WebSocket Server)
- DatabaseAdapter, DuckDbAdapter, SQLiteAdapter, ClickHouseAdapter
- CentralDataHopper (Universal Multi-Asset SQLite Vault)
- MacroEngine (FRED API & Treasury Yield Curve)
- SecEdgarClient (SEC EDGAR 10-K/10-Q XBRL history)
- MarketDataClient (Live Quotes, Beta, Shares Outstanding)
- DuckDbMacroStore (Columnar Macro Time-Series Warehouse)
"""

from cfa_quant.data.security_master import SecurityMaster
from cfa_quant.data.transaction_ledger import TransactionLedger, TaxLot, RealizedGainRecord
from cfa_quant.data.custodian_ingestion import CustodianIngestionGateway
from cfa_quant.data.news_wire import NewsWireEngine
from cfa_quant.data.news_websocket_server import NewsWebSocketServer
from cfa_quant.data.db_adapters import DatabaseAdapter, DuckDbAdapter, SQLiteAdapter, ClickHouseAdapter
from cfa_quant.hopper import CentralDataHopper
from pipeline.macro_engine import MacroEngine
from pipeline.sec_edgar_client import SecEdgarClient
from pipeline.market_data import MarketDataClient
from cfa_quant.data.analytics_store import AnalyticsStore
from cfa_quant.duckdb_macro_store import DuckDbMacroStore

__all__ = [
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
    "DuckDbMacroStore"
]
