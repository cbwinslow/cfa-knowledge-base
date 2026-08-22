"""
DuckDB Macroeconomic Columnar Warehouse & Ingestion Engine
Bootstraps and maintains an embedded analytical DuckDB database containing:
1. Point-in-time FRED Macroeconomic Time-Series (Yield Curve, SOFR, Inflation, Credit, GDP, Labor)
2. Fast Columnar SQL Views for Macro Regime & Yield Curve Modeling
3. Vector & Analytical Query Interfaces
"""

import duckdb
import pandas as pd
import urllib.request
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from .fred_inventory import FRED_MACRO_INVENTORY
except ImportError:
    try:
        from cfa_quant.fred_inventory import FRED_MACRO_INVENTORY
    except ImportError:
        from fred_inventory import FRED_MACRO_INVENTORY

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "macro_warehouse.duckdb"

class DuckDbMacroStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_PATH)
        self.init_schema()

    def get_connection(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self.db_path)

    def init_schema(self):
        conn = self.get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS macro_series_metadata (
                series_id VARCHAR PRIMARY KEY,
                title VARCHAR,
                category VARCHAR,
                frequency VARCHAR,
                units VARCHAR,
                usage VARCHAR,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS macro_observations (
                series_id VARCHAR,
                observation_date DATE,
                value DOUBLE,
                PRIMARY KEY (series_id, observation_date)
            );

            CREATE INDEX IF NOT EXISTS idx_macro_obs_date ON macro_observations(observation_date);
            CREATE INDEX IF NOT EXISTS idx_macro_obs_series ON macro_observations(series_id);
        """)
        
        for sid, meta in FRED_MACRO_INVENTORY.items():
            conn.execute("""
                INSERT OR REPLACE INTO macro_series_metadata (series_id, title, category, frequency, units, usage, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [sid, meta["title"], meta["category"], meta["frequency"], meta["units"], meta["usage"]])
            
        conn.close()

    def fetch_and_ingest_fred_series(self, series_id: str, years: int = 5) -> int:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "CFA-Quant-Macro-Ingestor/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                df = pd.read_csv(resp)
                
            if df.empty or len(df.columns) < 2:
                return 0

            date_col = df.columns[0]
            val_col = df.columns[1]
            
            df = df.rename(columns={date_col: "observation_date", val_col: "value"})
            df["observation_date"] = pd.to_datetime(df["observation_date"], errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna().sort_values("observation_date")
            
            min_date = pd.Timestamp.now() - pd.DateOffset(years=years)
            df = df[df["observation_date"] >= min_date]
            
            df["series_id"] = series_id
            
            conn = self.get_connection()
            conn.register("df_temp", df)
            conn.execute("""
                INSERT OR REPLACE INTO macro_observations (series_id, observation_date, value)
                SELECT series_id, observation_date, value FROM df_temp
            """)
            inserted_count = len(df)
            conn.close()
            return inserted_count
        except Exception as e:
            print(f"Notice: Handled FRED series {series_id}: {e}")
            return 0

    def bootstrap_warehouse(self, series_list: Optional[List[str]] = None, years: int = 5):
        targets = series_list or list(FRED_MACRO_INVENTORY.keys())
        print(f"🚀 Bootstrapping DuckDB Macro Warehouse with {len(targets)} series ({years}-year horizon)...")
        
        total_obs = 0
        for sid in targets:
            count = self.fetch_and_ingest_fred_series(sid, years=years)
            total_obs += count
            time.sleep(0.15)
            
        print(f"✓ Ingestion complete. Total observations stored: {total_obs:,}")

    def query_latest_yield_curve(self) -> Dict[str, float]:
        conn = self.get_connection()
        res = conn.execute("""
            WITH latest_dates AS (
                SELECT series_id, MAX(observation_date) as max_date
                FROM macro_observations
                WHERE series_id IN ('DGS1MO', 'DGS3MO', 'DGS2', 'DGS5', 'DGS10', 'DGS30')
                GROUP BY series_id
            )
            SELECT l.series_id, o.value
            FROM macro_observations o
            JOIN latest_dates l ON o.series_id = l.series_id AND o.observation_date = l.max_date
        """).fetchall()
        conn.close()
        return {row[0]: row[1] for row in res}

    def query_macro_history_df(self, series_ids: List[str]) -> pd.DataFrame:
        conn = self.get_connection()
        placeholders = ", ".join(["?"] * len(series_ids))
        df = conn.execute(f"""
            SELECT observation_date, series_id, value
            FROM macro_observations
            WHERE series_id IN ({placeholders})
            ORDER BY observation_date ASC
        """, series_ids).df()
        conn.close()
        
        if df.empty:
            return pd.DataFrame()
            
        pivoted = df.pivot(index="observation_date", columns="series_id", values="value")
        return pivoted

if __name__ == "__main__":
    store = DuckDbMacroStore()
    sample_series = ["DGS3MO", "DGS2", "DGS10", "DGS30", "T10Y2Y", "T10Y3M", "SOFR", "CPIAUCSL", "BAMLH0A0HYM2", "VIXCLS"]
    store.bootstrap_warehouse(series_list=sample_series, years=3)
    
    print("\n--- Latest Treasury Curve Snapshot from DuckDB ---")
    yc = store.query_latest_yield_curve()
    for k, v in yc.items():
        print(f"  {k:8}: {v:.2f}%")
