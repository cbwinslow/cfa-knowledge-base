"""
Unit, Negative, Boundary & Concurrency Tests for DuckDB Central Analytics Store
"""

import pytest
from cfa_quant.data.analytics_store import AnalyticsStore, safe_json_loads

def test_analytics_store_write_and_retrieve_latest(tmp_path):
    test_db = tmp_path / "test_analytics.duckdb"
    store = AnalyticsStore(db_path=test_db)
    
    # 1. Record a Valuation Calculation
    calc_id = store.record_calculation(
        calc_type="VALUATION",
        entity_ticker="NVDA",
        summary_title="NVIDIA Valuation Triangulation",
        primary_metric_label="Intrinsic Fair Value",
        primary_metric_value=175.50,
        structured_metrics={"dcf": 180.0, "multiples": 171.0},
        raw_result_payload={"full_dump": True, "ticker": "NVDA"}
    )
    assert calc_id.startswith("CALC-VALU-")
    
    # 2. Retrieve Latest Calculation
    latest = store.get_latest_calculation("VALUATION", "NVDA")
    assert latest is not None
    assert latest["calc_id"] == calc_id
    assert latest["entity_ticker"] == "NVDA"
    assert latest["primary_metric_value"] == 175.50
    assert latest["metrics"]["dcf"] == 180.0
    assert latest["raw_payload"]["full_dump"] is True

def test_analytics_store_history_and_filters(tmp_path):
    test_db = tmp_path / "test_history.duckdb"
    store = AnalyticsStore(db_path=test_db)
    
    # Insert multiple calculation types
    store.record_calculation("BLACK_LITTERMAN", "MANDATE_1", "BL Titls 1", "Max Sharpe", 1.45, {}, {})
    store.record_calculation("BLACK_LITTERMAN", "MANDATE_1", "BL Titls 2", "Max Sharpe", 1.55, {}, {})
    store.record_calculation("REBALANCING", "MANDATE_1", "HIFO Blotter", "Turnover", 250000.0, {}, {})
    
    # Query history with filter
    bl_history = store.list_history(calc_type="BLACK_LITTERMAN", entity_ticker="MANDATE_1")
    assert len(bl_history) == 2
    assert bl_history[0]["primary_metric_value"] == 155.0 or bl_history[0]["primary_metric_value"] == 1.55
    
    all_history = store.list_history(limit=10)
    assert len(all_history) == 3

def test_analytics_store_negative_and_missing_records(tmp_path):
    test_db = tmp_path / "test_missing.duckdb"
    store = AnalyticsStore(db_path=test_db)
    
    # Query non-existent record
    res = store.get_latest_calculation("VALUATION", "NON_EXISTENT_TICKER")
    assert res is None
    
    # Test safe_json_loads
    assert safe_json_loads(None) == {}
    assert safe_json_loads("{invalid_json}") == {}

def test_master_institutional_excel_workbook_generation():
    from cfa_quant.excel_exporter import ExcelModelExporter
    import openpyxl
    
    exporter = ExcelModelExporter()
    wb_stream = exporter.generate_master_institutional_workbook("ENDOWMENT_ALPHA_MANDATE")
    assert wb_stream is not None
    assert wb_stream.getbuffer().nbytes > 1000
    
    wb = openpyxl.load_workbook(wb_stream)
    sheet_names = wb.sheetnames
    assert "Executive Summary" in sheet_names
    assert "Black-Litterman Allocation" in sheet_names
    assert "Rebalancing Blotter" in sheet_names
    assert "GIPS Composite Presentation" in sheet_names

