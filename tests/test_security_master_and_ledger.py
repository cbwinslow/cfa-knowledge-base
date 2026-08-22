"""
Unit Tests for Universal Security Master and DuckDB Transaction Ledger
"""

import pytest
import pandas as pd
from cfa_quant.data.security_master import SecurityMaster
from cfa_quant.data.transaction_ledger import TransactionLedger

def test_identifier_type_detection():
    sm = SecurityMaster()
    
    assert sm.detect_identifier_type("US0378331005") == "ISIN"
    assert sm.detect_identifier_type("037833100") == "CUSIP"
    assert sm.detect_identifier_type("BBG000B9XRY4") == "FIGI"
    assert sm.detect_identifier_type("2046251") == "SEDOL"
    assert sm.detect_identifier_type("AAPL") == "TICKER"
    assert sm.detect_identifier_type("MSFT") == "TICKER"

def test_security_master_resolution_and_hydration():
    sm = SecurityMaster()
    
    # Resolve CUSIP
    res_cusip = sm.resolve_security("037833100")
    assert res_cusip["ticker"] == "AAPL"
    assert res_cusip["asset_class"] == "Global Equities"
    
    # Hydrate CUSIP to typed instrument
    inst, dollars = sm.hydrate_instrument("037833100", quantity=50)
    assert inst.name == "Apple Inc."
    assert inst.compute_expected_return() > 0.0

def test_duckdb_transaction_ledger_hifo_tax_lot_matching(tmp_path):
    # Use temporary DuckDB for test isolation
    test_db = tmp_path / "test_ledger.duckdb"
    ledger = TransactionLedger(db_path=test_db)
    
    trades = [
        {"trade_id": "T1", "portfolio_id": "P_TEST", "instrument_id": "037833100", "ticker": "AAPL", "trade_date": "2025-01-10", "side": "BUY", "quantity": 100, "price": 200.0},
        {"trade_id": "T2", "portfolio_id": "P_TEST", "instrument_id": "037833100", "ticker": "AAPL", "trade_date": "2025-03-15", "side": "BUY", "quantity": 100, "price": 250.0},
        # Sell 100 shares @ $300 (HIFO must sell the $250 lot, realizing $50 gain instead of $100 gain)
        {"trade_id": "T3", "portfolio_id": "P_TEST", "instrument_id": "037833100", "ticker": "AAPL", "trade_date": "2026-05-01", "side": "SELL", "quantity": 100, "price": 300.0}
    ]
    
    df = pd.DataFrame(trades)
    n = ledger.ingest_transactions_batch(df)
    assert n == 3
    
    port, summary = ledger.reconstruct_portfolio_at_date("P_TEST", as_of_date="2026-06-01", tax_lot_strategy="HIFO")
    
    # HIFO should realize (300 - 250) * 100 = $5,000 gain
    assert summary["total_realized_capital_gains_usd"] == 5000.0, f"Expected $5,000 gain under HIFO, got {summary['total_realized_capital_gains_usd']}"
    assert len(summary["realized_trade_records"]) == 1
    assert summary["realized_trade_records"][0].cost_basis_per_unit == 250.0
