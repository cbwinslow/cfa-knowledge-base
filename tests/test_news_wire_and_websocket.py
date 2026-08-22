"""
Unit & Async Integration Tests for News Wire Engine and WebSocket Server
"""

import asyncio
import json
import pytest
import websockets
from cfa_quant.data.news_wire import NewsWireEngine
from cfa_quant.data.news_websocket_server import NewsWebSocketServer

def test_news_wire_vector_ingestion_and_search(tmp_path):
    test_db = tmp_path / "test_news.duckdb"
    engine = NewsWireEngine(db_path=test_db)
    
    # Insert a synthetic breaking 8-K article directly into DuckDB
    conn = engine._get_connection()
    conn.execute("""
        INSERT INTO news_articles (
            article_id, source_wire, wire_channel, ticker, title, summary, url, published_at, raw_payload_json
        ) VALUES (
            'TEST-001', 'SEC_8K_MATERIAL_EVENTS', 'SEC_8K', 'AAPL',
            'Apple Inc. Announces Strategic Autonomous AI Chip Partnership',
            'Material definitive agreement for next-generation silicon architecture.',
            'https://sec.gov/Archives/edgar/data/320193/test.htm',
            CURRENT_TIMESTAMP, '{"raw": true}'
        );
    """)
    conn.close()
    
    # Perform vector semantic search
    matches = engine.search_news_wire("autonomous silicon chip partnership", ticker="AAPL", top_k=1)
    assert len(matches) == 1
    assert matches[0]["ticker"] == "AAPL"
    assert "Autonomous AI Chip" in matches[0]["title"]

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

    asyncio.run(_run_ws_test())
