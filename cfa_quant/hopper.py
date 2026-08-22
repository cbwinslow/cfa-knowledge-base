"""
Universal Data Hopper & Intake Vault
Centralized, persistent multi-asset data lake and ingestion gateway for:
1. Ingesting raw JSON, CSV, text intake notes, and brokerage extracts
2. Normalizing and registering standardized investment instruments
3. Storing and retrieving multi-asset portfolios and client life-cycle profiles
4. Managing macroeconomic stress scenarios
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import pandas as pd

try:
    from .instruments.base import InvestmentInstrument, AssetClass
    from .instruments.fixed_income import FixedCouponBond, ZeroCouponBond, InflationLinkedBond
    from .instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
    from .instruments.derivatives_fx import InterestRateSwap, ForexForward, EquityIndexFutures, OptionsContract
    from .instruments.portfolio import UnifiedPortfolio
except ImportError:
    try:
        from cfa_quant.instruments.base import InvestmentInstrument, AssetClass
        from cfa_quant.instruments.fixed_income import FixedCouponBond, ZeroCouponBond, InflationLinkedBond
        from cfa_quant.instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
        from cfa_quant.instruments.derivatives_fx import InterestRateSwap, ForexForward, EquityIndexFutures, OptionsContract
        from cfa_quant.instruments.portfolio import UnifiedPortfolio
    except ImportError:
        from instruments.base import InvestmentInstrument, AssetClass
        from instruments.fixed_income import FixedCouponBond, ZeroCouponBond, InflationLinkedBond
        from instruments.equity import PublicEquityStock, RealEstateAsset, PrivateEquityHolding
        from instruments.derivatives_fx import InterestRateSwap, ForexForward, EquityIndexFutures, OptionsContract
        from instruments.portfolio import UnifiedPortfolio

HOPPER_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "central_hopper.sqlite"

class CentralDataHopper:
    def __init__(self, db_path: Path = HOPPER_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            # 1. Raw Ingestion Payloads Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS intake_payloads (
                    payload_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_tag TEXT NOT NULL,
                    payload_type TEXT NOT NULL,
                    raw_content TEXT NOT NULL,
                    parsed_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 2. Registered Standardized Portfolios Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS portfolios (
                    portfolio_id TEXT PRIMARY KEY,
                    portfolio_name TEXT NOT NULL,
                    client_name TEXT,
                    risk_tolerance TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata_json TEXT
                );
            """)
            
            # 3. Portfolio Holdings / Instruments Table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    portfolio_id TEXT NOT NULL,
                    instrument_name TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    current_market_price REAL NOT NULL,
                    dollar_allocation REAL NOT NULL,
                    attributes_json TEXT NOT NULL,
                    FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id) ON DELETE CASCADE
                );
            """)
            
            # 4. Macro Stress Test Scenarios Catalog
            cur.execute("""
                CREATE TABLE IF NOT EXISTS macro_scenarios (
                    scenario_id TEXT PRIMARY KEY,
                    scenario_name TEXT NOT NULL,
                    description TEXT,
                    shocks_json TEXT NOT NULL
                );
            """)
            
            cur.execute("SELECT COUNT(*) as count FROM macro_scenarios;")
            if cur.fetchone()["count"] == 0:
                self._seed_default_scenarios(cur)
                
            conn.commit()

    def _seed_default_scenarios(self, cur: sqlite3.Cursor):
        scenarios = [
            (
                "stagflation_1970s",
                "1970s Severe Stagflation Shock",
                "Inflation surges +300 bps, central bank hikes rates +250 bps, equities decline, commodities surge.",
                json.dumps({
                    "Global Equities": -0.18,
                    "Fixed Income": -0.12,
                    "Real Estate": 0.04,
                    "Commodities": 0.35,
                    "Private Equity": -0.15,
                    "Cash & Equivalents": 0.05
                })
            ),
            (
                "gfc_2008",
                "2008 Global Financial Crisis Liquidity Shock",
                "Severe equity sell-off (-38%), real estate crash (-25%), flight to safety into Treasuries (+12%).",
                json.dumps({
                    "Global Equities": -0.38,
                    "Fixed Income": 0.12,
                    "Real Estate": -0.25,
                    "Commodities": -0.40,
                    "Private Equity": -0.30,
                    "Cash & Equivalents": 0.01
                })
            ),
            (
                "rate_hike_2022",
                "2022 Rapid Monetary Tightening Shock",
                "Both equities (-19%) and fixed income (-14%) fall simultaneously as inflation breaks stock-bond correlation.",
                json.dumps({
                    "Global Equities": -0.19,
                    "Fixed Income": -0.14,
                    "Real Estate": -0.10,
                    "Commodities": 0.18,
                    "Private Equity": -0.12,
                    "Cash & Equivalents": 0.045
                })
            ),
            (
                "ai_productivity_boom",
                "AI & Technological Productivity Boom",
                "Strong non-inflationary growth: equities surge (+30%), real estate expands (+8%), rates remain stable.",
                json.dumps({
                    "Global Equities": 0.30,
                    "Fixed Income": 0.04,
                    "Real Estate": 0.08,
                    "Commodities": 0.05,
                    "Private Equity": 0.25,
                    "Cash & Equivalents": 0.035
                })
            )
        ]
        cur.executemany("INSERT INTO macro_scenarios (scenario_id, scenario_name, description, shocks_json) VALUES (?, ?, ?, ?);", scenarios)

    def ingest_raw_payload(self, raw_content: str, payload_type: str = "json", source_tag: str = "user_intake") -> int:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO intake_payloads (source_tag, payload_type, raw_content) VALUES (?, ?, ?);",
                (source_tag, payload_type, raw_content)
            )
            payload_id = cur.lastrowid
            conn.commit()
            return int(payload_id)

    def save_portfolio(self, portfolio_id: str, portfolio: UnifiedPortfolio, client_name: str = "Client", risk_tolerance: str = "Moderate", metadata: Optional[Dict[str, Any]] = None):
        with self._get_connection() as conn:
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO portfolios (portfolio_id, portfolio_name, client_name, risk_tolerance, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(portfolio_id) DO UPDATE SET
                    portfolio_name = excluded.portfolio_name,
                    client_name = excluded.client_name,
                    risk_tolerance = excluded.risk_tolerance,
                    metadata_json = excluded.metadata_json;
            """, (portfolio_id, portfolio.name, client_name, risk_tolerance, json.dumps(metadata or {})))
            
            cur.execute("DELETE FROM portfolio_holdings WHERE portfolio_id = ?;", (portfolio_id,))
            
            holding_rows = []
            for inst, dollars in portfolio.holdings:
                holding_rows.append((
                    portfolio_id,
                    inst.name,
                    inst.asset_class.value,
                    inst.current_market_price,
                    dollars,
                    json.dumps(inst.to_dict())
                ))
                
            cur.executemany("""
                INSERT INTO portfolio_holdings (portfolio_id, instrument_name, asset_class, current_market_price, dollar_allocation, attributes_json)
                VALUES (?, ?, ?, ?, ?, ?);
            """, holding_rows)
            
            conn.commit()

    def load_portfolio(self, portfolio_id: str) -> Optional[UnifiedPortfolio]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM portfolios WHERE portfolio_id = ?;", (portfolio_id,))
            p_row = cur.fetchone()
            if not p_row:
                return None
                
            port = UnifiedPortfolio(name=p_row["portfolio_name"])
            
            cur.execute("SELECT * FROM portfolio_holdings WHERE portfolio_id = ?;", (portfolio_id,))
            rows = cur.fetchall()
            
            for r in rows:
                attr = json.loads(r["attributes_json"])
                ac = r["asset_class"]
                dollars = float(r["dollar_allocation"])
                
                if ac == AssetClass.FIXED_INCOME.value:
                    inst = FixedCouponBond(
                        name=r["instrument_name"],
                        coupon_rate=attr.get("coupon_rate", 0.045),
                        maturity_years=attr.get("duration_years", 7.0),
                        yield_to_maturity=attr.get("expected_return_pct", 4.5)/100.0
                    )
                elif ac == AssetClass.REAL_ESTATE.value:
                    inst = RealEstateAsset(name=r["instrument_name"], net_operating_income=dollars * 0.055, cap_rate=0.055)
                elif ac == AssetClass.PRIVATE_EQUITY.value:
                    inst = PrivateEquityHolding(name=r["instrument_name"], target_irr=attr.get("expected_return_pct", 15.0)/100.0)
                else:
                    inst = PublicEquityStock(
                        name=r["instrument_name"],
                        beta=attr.get("beta", 1.0),
                        expected_earnings_growth=attr.get("expected_return_pct", 7.5)/100.0,
                        historical_volatility=attr.get("volatility_pct", 18.0)/100.0
                    )
                    
                port.add_instrument(inst, dollars)
                
            return port

    def list_all_portfolios(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT portfolio_id, portfolio_name, client_name, risk_tolerance, created_at FROM portfolios;")
            return [dict(row) for row in cur.fetchall()]

    def list_all_scenarios(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM macro_scenarios;")
            res = []
            for r in cur.fetchall():
                d = dict(r)
                d["shocks"] = json.loads(d["shocks_json"])
                res.append(d)
            return res

if __name__ == "__main__":
    hopper = CentralDataHopper()
    print("=" * 70)
    print("🏛️ CENTRAL DATA HOPPER & INGESTION VAULT")
    print("=" * 70)
    print(f"Hopper Database Location: {hopper.db_path}")
    scenarios = hopper.list_all_scenarios()
    print(f"Active Macro Scenarios Loaded: {len(scenarios)}")
    for s in scenarios:
        print(f"  • {s['scenario_name']} ({s['scenario_id']})")
    print("=" * 70)
