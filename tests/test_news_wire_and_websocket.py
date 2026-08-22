"""
Comprehensive Unit, Negative, Boundary, and Integration Tests for News Wire & WebSocket Engine
"""

import asyncio
import json
import pytest
import websockets
from cfa_quant.data.news_wire import NewsWireEngine, safe_json_loads
from cfa_quant.data.news_websocket_server import NewsWebSocketServer

def test_news_wire_vector_ingestion_and_search(tmp_path):
    test_db = tmp_path / "test_news.duckdb"
    engine = NewsWireEngine(db_path=test_db)
    
    # Insert a synthetic breaking 8-K article directly into DuckDB
    conn = engine._get_connection()
    conn.execute("""
        INSERT INTO news_articles (
            article_id, source_wire, wire_channel, ticker, headline, title, summary, url, domain, published_at, raw_payload_json
        ) VALUES (
            'TEST-001', 'SEC_8K_MATERIAL_EVENTS', 'SEC_8K', 'AAPL',
            'Apple Inc. Announces Strategic Autonomous AI Chip Partnership',
            'Apple Inc. Announces Strategic Autonomous AI Chip Partnership',
            'Material definitive agreement for next-generation silicon architecture.',
            'https://sec.gov/Archives/edgar/data/320193/test.htm', 'sec.gov',
            CURRENT_TIMESTAMP, '{"raw": true}'
        );
    """)
    conn.close()
    
    # Perform vector semantic search
    matches = engine.search_news_wire("autonomous silicon chip partnership", ticker="AAPL", top_k=1)
    assert len(matches) == 1
    assert matches[0]["ticker"] == "AAPL"
    assert "Autonomous AI Chip" in matches[0]["title"]

def test_news_wire_negative_and_corrupt_inputs(tmp_path):
    """
    Negative Testing: Tests graceful degradation on corrupt feeds, missing fields,
    malformed HTML, and invalid timestamps without crashing.
    """
    test_db = tmp_path / "test_corrupt.duckdb"
    engine = NewsWireEngine(db_path=test_db)
    
    # 1. Test completely empty/corrupt entry dictionary
    corrupt_entry = {"title": "", "link": "", "summary": "<invalid<html<<>>"}
    meta = engine.extract_rich_metadata(corrupt_entry, raw_summary_html="<b>Broken</b>", link="not_a_valid_url")
    assert meta["domain"] == "financial-wire" or meta["domain"] == "not_a_valid_url"
    assert isinstance(meta["subjects"], list)
    assert isinstance(meta["media_urls"], list)
    
    # 2. Test safe_json_loads with non-string / corrupt inputs
    assert safe_json_loads(None) == []
    assert safe_json_loads(float('nan')) == []
    assert safe_json_loads("{invalid:json}") == []
    assert safe_json_loads('["AAPL", "MSFT"]') == ["AAPL", "MSFT"]
    assert safe_json_loads({"already": "dict"}, default={}) == {"already": "dict"}
    
    # 3. Test searching on empty database
    empty_matches = engine.search_news_wire("query with zero records in db", ticker="NONEXISTENT")
    assert empty_matches == []

def test_quality_score_and_sentiment_boundary_invariants(tmp_path):
    """
    Boundary Testing: Mathematical verification of Quality Score in [0.0, 1.0]
    and Sentiment Polarity in [-1.0, 1.0].
    """
    test_db = tmp_path / "test_bounds.duckdb"
    engine = NewsWireEngine(db_path=test_db)
    
    # Test Quality Score Bounds
    q_empty = engine.compute_quality_score("", "", {}, 0.0)
    assert 0.0 <= q_empty <= 1.0, f"Quality score {q_empty} must be in [0.0, 1.0]"
    
    rich_meta = {
        "primary_ticker": "NVDA", "subjects": ["AI", "Earnings"],
        "domain": "wsj.com", "author": "John Doe",
        "lead_image_url": "https://images.wsj.net/im-1.jpg", "media_urls": ["url1", "url2"]
    }
    q_rich = engine.compute_quality_score("NVIDIA Reports Record Q4 Revenue and Surging AI Demand", "Comprehensive financial overview with $30B net profit.", rich_meta, 0.8)
    assert 0.7 <= q_rich <= 1.0, f"Rich quality score {q_rich} should be high"
    
    # Test Sentiment Score Bounds
    bullish_text = "Record surge in profits beats all expectations with massive expansion and dividend boost."
    bearish_text = "Massive plunge in earnings misses estimates as lawsuit and downgrade trigger catastrophic losses."
    neutral_text = "Company held regular board meeting to discuss standard procedural items."
    
    s_bull = engine.compute_sentiment_score(bullish_text)
    s_bear = engine.compute_sentiment_score(bearish_text)
    s_neut = engine.compute_sentiment_score(neutral_text)
    
    assert s_bull > 0.0, f"Bullish sentiment must be positive: {s_bull}"
    assert s_bear < 0.0, f"Bearish sentiment must be negative: {s_bear}"
    assert -1.0 <= s_bull <= 1.0
    assert -1.0 <= s_bear <= 1.0
    assert s_neut == 0.0

def test_websocket_server_handshake_and_query(tmp_path):
    async def _run_ws_test():
        test_db = tmp_path / "test_ws_news.duckdb"
        engine = NewsWireEngine(db_path=test_db)
        server = NewsWebSocketServer(host="127.0.0.1", port=8799, engine=engine)
        
        # Start WebSocket server task
        async with websockets.serve(server.handle_client, "127.0.0.1", 8799):
            # Connect client
            async with websockets.connect("ws://127.0.0.1:8799") as ws:
                # 1. Receive Welcome Handshake
                welcome = json.loads(await ws.recv())
                assert welcome["event"] == "SYSTEM_WELCOME"
                
                # 2. Test Ping / Pong
                await ws.send(json.dumps({"action": "PING"}))
                pong = json.loads(await ws.recv())
                assert pong["event"] == "PONG"
                
                # 3. Test Subscription Update
                await ws.send(json.dumps({"action": "SUBSCRIBE", "channels": ["TICKER:NVDA", "SEC_8K"]}))
                sub_ack = json.loads(await ws.recv())
                assert sub_ack["event"] == "SUBSCRIPTION_UPDATED"
                assert "TICKER:NVDA" in sub_ack["active_channels"]
                
                # 4. Negative Test: Malformed Non-JSON Message
                await ws.send("MALFORMED_NON_JSON_PACKET_!@#$")
                err_resp = json.loads(await ws.recv())
                assert "error" in err_resp

    asyncio.run(_run_ws_test())
