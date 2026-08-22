"""
Centralized Data Ingestion & Warehouse Package
Exports:
- CentralDataHopper (Universal Multi-Asset SQLite Vault)
- MacroEngine (FRED API & Treasury Yield Curve)
- SecEdgarClient (SEC EDGAR 10-K/10-Q XBRL history)
- MarketDataClient (Live Quotes, Beta, Shares Outstanding)
- DuckDbMacroStore (Columnar Macro Time-Series Warehouse)
"""

from cfa_quant.hopper import CentralDataHopper
from pipeline.macro_engine import MacroEngine
from pipeline.sec_edgar_client import SecEdgarClient
from pipeline.market_data import MarketDataClient
from cfa_quant.duckdb_macro_store import DuckDbMacroStore

__all__ = [
    "CentralDataHopper",
    "MacroEngine",
    "SecEdgarClient",
    "MarketDataClient",
    "DuckDbMacroStore"
]
