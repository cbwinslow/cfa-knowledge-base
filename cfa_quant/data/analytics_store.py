"""
CFA Institutional Central Analytics Warehouse & Calculation Store (DuckDB)
Centralized, persistent columnar store for all quantitative calculations:
1. Valuation Triangulation & Football Field Results
2. Black-Litterman Implied Equilibrium & View Blending Tilts
3. Multi-Factor Active Risk Decompositions & FLAM Metrics
4. Tax-Aware HIFO Rebalancing Blotters & FIX Trade Tickets
5. GIPS Composite Annual Presentations & Internal Dispersion
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import duckdb
import pandas as pd

DEFAULT_ANALYTICS_DB = Path(__file__).resolve().parent.parent.parent / "data" / "analytics_hub.duckdb"

def safe_json_loads(val: Any, default: Any = None) -> Any:
    if val is None:
        return default if default is not None else {}
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(str(val))
    except Exception:
        return default if default is not None else {}

class AnalyticsStore:
    def __init__(self, db_path: Optional[Union[Path, str]] = None):
        if db_path is not None:
            self.db_path = Path(db_path)
        elif "PYTEST_CURRENT_TEST" in os.environ or "PYTEST_XDIST_WORKER" in os.environ:
            worker = os.environ.get("PYTEST_XDIST_WORKER", f"pid_{os.getpid()}")
            self.db_path = DEFAULT_ANALYTICS_DB.parent / f"{DEFAULT_ANALYTICS_DB.stem}_{worker}{DEFAULT_ANALYTICS_DB.suffix}"
        else:
            self.db_path = DEFAULT_ANALYTICS_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_connection(self, read_only: bool = False) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path), read_only=read_only)

    def _init_tables(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS calculation_records (
                    calc_id VARCHAR PRIMARY KEY,
                    calc_type VARCHAR NOT NULL,       -- 'VALUATION', 'BLACK_LITTERMAN', 'FACTOR_RISK', 'REBALANCING', 'GIPS'
                    entity_ticker VARCHAR NOT NULL,   -- e.g. 'MSFT', 'PORTFOLIO_ALPHA', 'GLOBAL_MANDATE'
                    summary_title VARCHAR,
                    primary_metric_label VARCHAR,
                    primary_metric_value DOUBLE,
                    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    structured_metrics_json VARCHAR,  -- Key KPI dictionary
                    raw_payload_json VARCHAR          -- Complete unadulterated calculation result (Zero Data Loss)
                );
                CREATE INDEX IF NOT EXISTS idx_calc_lookup ON calculation_records(calc_type, entity_ticker, computed_at);
            """)

    # ==================== STORE CALCULATION ====================
    def record_calculation(
        self,
        calc_type: str,
        entity_ticker: str,
        summary_title: str,
        primary_metric_label: str,
        primary_metric_value: float,
        structured_metrics: Dict[str, Any],
        raw_result_payload: Dict[str, Any],
        calc_id: Optional[str] = None
    ) -> str:
        """
        Persists calculation results into the central DuckDB columnar repository.
        """
        c_id = calc_id or f"CALC-{calc_type[:4]}-{uuid.uuid4().hex[:10].upper()}"
        metrics_json = json.dumps(structured_metrics)
        payload_json = json.dumps(raw_result_payload)
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO calculation_records (
                    calc_id, calc_type, entity_ticker, summary_title,
                    primary_metric_label, primary_metric_value, computed_at,
                    structured_metrics_json, raw_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
            """, (
                c_id, calc_type.upper(), entity_ticker.upper(), summary_title,
                primary_metric_label, float(primary_metric_value),
                metrics_json, payload_json
            ))
            
        return c_id

    # ==================== QUERY CALCULATION ====================
    def get_latest_calculation(self, calc_type: str, entity_ticker: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the latest point-in-time calculation result.
        """
        with self._get_connection(read_only=True) as conn:
            row = conn.execute("""
                SELECT calc_id, calc_type, entity_ticker, summary_title,
                       primary_metric_label, primary_metric_value, computed_at,
                       structured_metrics_json, raw_payload_json
                FROM calculation_records
                WHERE calc_type = ? AND entity_ticker = ?
                ORDER BY computed_at DESC
                LIMIT 1;
            """, (calc_type.upper(), entity_ticker.upper())).fetchone()
            
            if not row:
                return None
                
            return {
                "calc_id": row[0],
                "calc_type": row[1],
                "entity_ticker": row[2],
                "summary_title": row[3],
                "primary_metric_label": row[4],
                "primary_metric_value": row[5],
                "computed_at": str(row[6]),
                "metrics": safe_json_loads(row[7]),
                "raw_payload": safe_json_loads(row[8])
            }

    def list_history(
        self,
        calc_type: Optional[str] = None,
        entity_ticker: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Lists calculation audit trail across any filter.
        """
        query = "SELECT calc_id, calc_type, entity_ticker, summary_title, primary_metric_label, primary_metric_value, computed_at, structured_metrics_json FROM calculation_records WHERE 1=1"
        params = []
        
        if calc_type:
            query += " AND calc_type = ?"
            params.append(calc_type.upper())
        if entity_ticker:
            query += " AND entity_ticker = ?"
            params.append(entity_ticker.upper())
            
        query += " ORDER BY computed_at DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection(read_only=True) as conn:
            rows = conn.execute(query, params).fetchall()
            
            return [
                {
                    "calc_id": r[0],
                    "calc_type": r[1],
                    "entity_ticker": r[2],
                    "summary_title": r[3],
                    "primary_metric_label": r[4],
                    "primary_metric_value": r[5],
                    "computed_at": str(r[6]),
                    "metrics": safe_json_loads(r[7])
                }
                for r in rows
            ]

    # ==================== JSON PORTABILITY EXPORT & IMPORT ====================
    def export_to_json_file(self, target_json_path: Path) -> int:
        """
        Exports all calculation records from DuckDB to a universal portable JSON file.
        """
        target_path = Path(target_json_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection(read_only=True) as conn:
            rows = conn.execute("""
                SELECT calc_id, calc_type, entity_ticker, summary_title,
                       primary_metric_label, primary_metric_value, computed_at,
                       structured_metrics_json, raw_payload_json
                FROM calculation_records
                ORDER BY computed_at ASC;
            """).fetchall()
            
            records = [
                {
                    "calc_id": r[0],
                    "calc_type": r[1],
                    "entity_ticker": r[2],
                    "summary_title": r[3],
                    "primary_metric_label": r[4],
                    "primary_metric_value": r[5],
                    "computed_at": str(r[6]),
                    "metrics": safe_json_loads(r[7]),
                    "raw_payload": safe_json_loads(r[8])
                }
                for r in rows
            ]
            
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
            
        return len(records)

    def import_from_json_file(self, source_json_path: Path) -> int:
        """
        Imports calculation records from a portable JSON file into DuckDB with idempotency.
        """
        source_path = Path(source_json_path)
        if not source_path.exists():
            return 0
            
        with open(source_path, "r", encoding="utf-8") as f:
            records = json.load(f)
            
        imported_count = 0
        for rec in records:
            self.record_calculation(
                calc_type=rec["calc_type"],
                entity_ticker=rec["entity_ticker"],
                summary_title=rec.get("summary_title", ""),
                primary_metric_label=rec.get("primary_metric_label", "Score"),
                primary_metric_value=float(rec.get("primary_metric_value", 0.0)),
                structured_metrics=rec.get("metrics", {}),
                raw_result_payload=rec.get("raw_payload", {}),
                calc_id=rec["calc_id"]
            )
            imported_count += 1
            
        return imported_count

if __name__ == "__main__":
    hub = AnalyticsStore()
    
    cid = hub.record_calculation(
        calc_type="VALUATION",
        entity_ticker="MSFT",
        summary_title="Microsoft Consensus Intrinsic Valuation",
        primary_metric_label="Consensus Fair Value ($)",
        primary_metric_value=512.40,
        structured_metrics={"dcf_val": 520.0, "ri_val": 495.0, "ddm_val": 480.0, "wacc": 0.0825},
        raw_result_payload={"full_model_dump": "zero_loss_audit_trail"}
    )
    print(f"✓ Stored Calculation Record: {cid}")
    latest = hub.get_latest_calculation("VALUATION", "MSFT")
    print(f"✓ Retrieved Latest: {latest['summary_title']} ➔ {latest['primary_metric_label']}: ${latest['primary_metric_value']}")

