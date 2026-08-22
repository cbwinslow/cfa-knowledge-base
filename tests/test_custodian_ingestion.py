"""
Unit Tests for Multi-Custodian Trade Statement Ingestion Gateway
"""

import io
import pytest
from cfa_quant.data.custodian_ingestion import CustodianIngestionGateway
from cfa_quant.data.transaction_ledger import TransactionLedger

def test_schwab_csv_ingestion(tmp_path):
    test_db = tmp_path / "test_schwab.duckdb"
    ledger = TransactionLedger(db_path=test_db)
    gateway = CustodianIngestionGateway(ledger=ledger)
    
    schwab_data = """Date,Action,Symbol,Description,Quantity,Price,Fees & Comm,Amount
2025-01-10,Buy,AAPL,APPLE INC,100,$200.00,$0.00,"-$20,000.00"
2025-06-15,Buy,MSFT,MICROSOFT CORP,50,$400.00,$0.00,"-$20,000.00"
2026-08-01,Sell,AAPL,APPLE INC,50,$300.00,$0.00,"$15,000.00"
"""
    res = gateway.ingest_custodial_file(io.StringIO(schwab_data), portfolio_id="TEST_SCHWAB")
    
    assert res["status"] == "success"
    assert res["detected_custodian"] == "SCHWAB"
    assert res["num_trades_ingested"] == 3
    assert res["reconstructed_portfolio_value_usd"] > 0.0
    # Gain on 50 AAPL @ $300 (Basis: $200) = $5,000
    assert res["realized_capital_gains_usd"] == 5000.0

def test_ibkr_flex_query_ingestion(tmp_path):
    test_db = tmp_path / "test_ibkr.duckdb"
    ledger = TransactionLedger(db_path=test_db)
    gateway = CustodianIngestionGateway(ledger=ledger)
    
    ibkr_data = """ClientAccountID,DateTime,Buy/Sell,Symbol,Quantity,TradePrice,IBCommission
U123456,2025-03-01 10:00:00,BUY,NVDA,200,100.00,1.00
U123456,2026-04-12 11:30:00,SELL,NVDA,100,150.00,1.00
"""
    res = gateway.ingest_custodial_file(io.StringIO(ibkr_data), portfolio_id="TEST_IBKR")
    
    assert res["status"] == "success"
    assert res["detected_custodian"] == "IBKR"
    assert res["num_trades_ingested"] == 2
    assert res["realized_capital_gains_usd"] == 5000.0
