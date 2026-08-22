"""
Unit Tests for Multi-Custodian, OFX, FIX Trade Statement Ingestion Gateway
"""

import io
import pytest
import pandas as pd
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
    assert res["detected_format"] == "SCHWAB"
    assert res["num_trades_ingested"] == 3
    assert res["reconstructed_portfolio_value_usd"] > 0.0
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
    assert res["detected_format"] == "IBKR"
    assert res["num_trades_ingested"] == 2
    assert res["realized_capital_gains_usd"] == 5000.0

def test_ofx_xml_statement_ingestion(tmp_path):
    test_db = tmp_path / "test_ofx.duckdb"
    ledger = TransactionLedger(db_path=test_db)
    gateway = CustodianIngestionGateway(ledger=ledger)
    
    ofx_sample = """<OFX><INVSTMTMSGSRSV1><INVSTMTTRNRS><INVSTMTRS>
<INVTRANLIST>
<BUYSTOCK><INVBUY><INVTRAN><DTTRADE>20250615120000</INVTRAN><SECID><UNIQUEID>AAPL</UNIQUEID></SECID><UNITS>300</UNITS><UNITPRICE>210.00</UNITPRICE><COMMISSION>0.00</COMMISSION></INVBUY></BUYSTOCK>
<SELLSTOCK><INVSELL><INVTRAN><DTTRADE>20260720120000</INVTRAN><SECID><UNIQUEID>AAPL</UNIQUEID></SECID><UNITS>100</UNITS><UNITPRICE>305.00</UNITPRICE><COMMISSION>0.00</COMMISSION></INVSELL></SELLSTOCK>
</INVTRANLIST></INVSTMTRS></INVSTMTTRNRS></INVSTMTMSGSRSV1></OFX>"""

    res = gateway.ingest_custodial_file(ofx_sample, portfolio_id="TEST_OFX")
    assert res["status"] == "success"
    assert res["detected_format"] == "OFX_QFX"
    assert res["num_trades_ingested"] == 2
    assert res["realized_capital_gains_usd"] == 9500.0  # (305 - 210) * 100 = 9500

def test_fix_protocol_execution_reports(tmp_path):
    test_db = tmp_path / "test_fix.duckdb"
    ledger = TransactionLedger(db_path=test_db)
    gateway = CustodianIngestionGateway(ledger=ledger)
    
    fix_sample = """8=FIX.4.2|35=8|11=ORD1001|55=MSFT|54=1|38=500|44=415.00|60=20250810-14:30:00|
8=FIX.4.2|35=8|11=ORD1002|55=MSFT|54=2|38=200|44=495.00|60=20260812-15:45:00|"""

    res = gateway.ingest_custodial_file(fix_sample, portfolio_id="TEST_FIX")
    assert res["status"] == "success"
    assert res["detected_format"] == "FIX_PROTOCOL"
    assert res["num_trades_ingested"] == 2
    assert res["realized_capital_gains_usd"] == 16000.0  # (495 - 415) * 200 = 16000

def test_corporate_stock_split(tmp_path):
    test_db = tmp_path / "test_split.duckdb"
    ledger = TransactionLedger(db_path=test_db)
    gateway = CustodianIngestionGateway(ledger=ledger)
    
    # 1. Buy 100 shares of NVDA at $500
    buy_trade = pd.DataFrame([{
        "trade_id": "T_SPLIT_1", "portfolio_id": "P_SPLIT", "instrument_id": "NVDA", "ticker": "NVDA",
        "trade_date": "2025-01-10", "side": "BUY", "quantity": 100, "price": 500.0
    }])
    ledger.ingest_transactions_batch(buy_trade)
    
    # 2. Apply 4-for-1 stock split (Quantity -> 400, Price -> 125)
    gateway.apply_stock_split("P_SPLIT", "NVDA", split_ratio=4.0, effective_date="2025-06-01")
    
    # 3. Sell 200 shares at $175 (Gain = 200 * (175 - 125) = $10,000)
    sell_trade = pd.DataFrame([{
        "trade_id": "T_SPLIT_2", "portfolio_id": "P_SPLIT", "instrument_id": "NVDA", "ticker": "NVDA",
        "trade_date": "2026-07-01", "side": "SELL", "quantity": 200, "price": 175.0
    }])
    ledger.ingest_transactions_batch(sell_trade)
    
    port, summary = ledger.reconstruct_portfolio_at_date("P_SPLIT", as_of_date="2026-12-31", tax_lot_strategy="HIFO")
    assert summary["total_realized_capital_gains_usd"] == 10000.0
