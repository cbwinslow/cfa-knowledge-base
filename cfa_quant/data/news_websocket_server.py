"""
Institutional Real-Time Financial News WebSocket Server
Streams breaking SEC 8-K filings, Federal Reserve wires, and equity news to connected clients.

Features:
1. Pub/Sub Channel Subscriptions ('ALL', 'SEC_8K', 'FOMC', 'TICKER:<SYMBOL>')
2. Background Asynchronous Wire Ingestion & Vectorization Worker
3. Idempotent Deduplication (Broadcasting only new material events)
4. Interactive WebSocket Query & Vector Search Interface
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
import websockets

try:
    from cfa_quant.data.news_wire import NewsWireEngine
except ImportError:
    from .news_wire import NewsWireEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("NewsWebSocketServer")

class NewsWebSocketServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8765, engine: Optional[NewsWireEngine] = None):
        self.host = host
        self.port = port
        self.engine = engine or NewsWireEngine()
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.subscriptions: Dict[websockets.WebSocketServerProtocol, Set[str]] = {}
        self.seen_article_ids: Set[str] = set()
        self._load_initial_seen_ids()

    def _load_initial_seen_ids(self):
        """Loads existing article IDs from DuckDB so we only broadcast fresh breaking events"""
        try:
            conn = self.engine._get_connection()
            rows = conn.execute("SELECT article_id FROM news_articles ORDER BY published_at DESC LIMIT 500;").fetchall()
            conn.close()
            self.seen_article_ids = {r[0] for r in rows}
        except Exception:
            self.seen_article_ids = set()

    # ==================== WEBSOCKET CLIENT HANDLER ====================
    async def handle_client(self, websocket):
        self.clients.add(websocket)
        self.subscriptions[websocket] = {"ALL"}  # Default channel
        logger.info(f"Client connected from {websocket.remote_address}. Total clients: {len(self.clients)}")
        
        # Send welcome handshake with system status
        welcome_msg = {
            "event": "SYSTEM_WELCOME",
            "server": "CFA Institutional News Wire Streamer v2.0",
            "timestamp": datetime.now().isoformat(),
            "subscribed_channels": list(self.subscriptions[websocket]),
            "available_channels": ["ALL", "SEC_8K", "FOMC", "TICKER:<SYMBOL>", "MACRO"]
        }
        await websocket.send(json.dumps(welcome_msg))
        
        try:
            async for raw_message in websocket:
                try:
                    msg = json.loads(raw_message)
                    action = msg.get("action", "").upper()
                    
                    if action == "SUBSCRIBE":
                        channels = msg.get("channels", ["ALL"])
                        if isinstance(channels, str):
                            channels = [channels]
                        self.subscriptions[websocket].update([c.upper() for c in channels])
                        ack = {"event": "SUBSCRIPTION_UPDATED", "active_channels": list(self.subscriptions[websocket])}
                        await websocket.send(json.dumps(ack))
                        
                    elif action == "UNSUBSCRIBE":
                        channels = msg.get("channels", [])
                        if isinstance(channels, str):
                            channels = [channels]
                        for c in channels:
                            self.subscriptions[websocket].discard(c.upper())
                        ack = {"event": "SUBSCRIPTION_UPDATED", "active_channels": list(self.subscriptions[websocket])}
                        await websocket.send(json.dumps(ack))
                        
                    elif action == "QUERY":
                        q = msg.get("query", "")
                        t = msg.get("ticker")
                        matches = self.engine.search_news_wire(q, ticker=t, top_k=msg.get("limit", 5))
                        resp = {"event": "QUERY_RESPONSE", "query": q, "ticker": t, "matches_count": len(matches), "results": matches}
                        await websocket.send(json.dumps(resp))
                        
                    elif action == "PING":
                        await websocket.send(json.dumps({"event": "PONG", "timestamp": datetime.now().isoformat()}))
                        
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({"error": "Invalid JSON format"}))
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.discard(websocket)
            self.subscriptions.pop(websocket, None)
            logger.info(f"Client disconnected. Active clients: {len(self.clients)}")

    # ==================== BROADCASTING ENGINE ====================
    async def broadcast_article(self, article: Dict[str, Any]):
        """
        Broadcasts a newly ingested article to all subscribed WebSocket clients.
        """
        if not self.clients:
            return
            
        ticker = str(article.get("ticker", "")).upper()
        channel = str(article.get("wire_channel", "")).upper()
        source = str(article.get("source_wire", "")).upper()
        
        payload = {
            "event": "BREAKING_NEWS",
            "article_id": article["article_id"],
            "source_wire": article["source_wire"],
            "wire_channel": article["wire_channel"],
            "ticker": ticker,
            "title": article["title"],
            "summary": article["summary"],
            "url": article["url"],
            "published_at": article["published_at"]
        }
        json_str = json.dumps(payload)
        
        # Send to matching clients
        dead_clients = set()
        for client in self.clients:
            subs = self.subscriptions.get(client, {"ALL"})
            is_match = (
                "ALL" in subs or
                channel in subs or
                ("SEC_8K" in subs and "SEC" in source) or
                ("FOMC" in subs and "FED" in source) or
                (f"TICKER:{ticker}" in subs if ticker else False)
            )
            if is_match:
                try:
                    await client.send(json_str)
                except Exception:
                    dead_clients.add(client)
                    
        for dc in dead_clients:
            self.clients.discard(dc)
            self.subscriptions.pop(dc, None)

    # ==================== BACKGROUND POLLING WORKER ====================
    async def background_wire_poller(self, interval_seconds: int = 60, monitored_tickers: Optional[List[str]] = None):
        """
        Continuously polls free news feeds in background, vectorizes, saves to DuckDB, and broadcasts.
        """
        tickers = monitored_tickers or ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "SPY"]
        logger.info(f"Starting Background News Poller (Interval: {interval_seconds}s | Tickers: {tickers})")
        
        while True:
            try:
                # 1. Ingest Macro & SEC wires
                self.engine.ingest_macro_and_sec_wires(max_articles_per_wire=5)
                
                # 2. Ingest Monitored Tickers
                for t in tickers:
                    self.engine.ingest_ticker_news(t, max_articles=3)
                    await asyncio.sleep(0.5)  # Throttle gracefully
                    
                # 3. Check for newly ingested articles in DuckDB
                conn = self.engine._get_connection()
                recent_rows = conn.execute("""
                    SELECT article_id, source_wire, wire_channel, ticker, title, summary, url, published_at
                    FROM news_articles
                    ORDER BY ingested_at DESC LIMIT 50;
                """).fetchall()
                conn.close()
                
                for r in recent_rows:
                    a_id = r[0]
                    if a_id not in self.seen_article_ids:
                        self.seen_article_ids.add(a_id)
                        art_dict = {
                            "article_id": r[0],
                            "source_wire": r[1],
                            "wire_channel": r[2],
                            "ticker": r[3],
                            "title": r[4],
                            "summary": r[5],
                            "url": r[6],
                            "published_at": str(r[7])
                        }
                        logger.info(f"⚡ [BROADCASTING] {art_dict['source_wire']} ➔ {art_dict['title'][:60]}...")
                        await self.broadcast_article(art_dict)
                        
            except Exception as e:
                logger.error(f"Error in background wire poller: {e}")
                
            await asyncio.sleep(interval_seconds)

    # ==================== SERVER START METHOD ====================
    async def start_server(self, interval_seconds: int = 60, monitored_tickers: Optional[List[str]] = None):
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"🏛️ CFA Institutional News Wire WebSocket Server running at ws://{self.host}:{self.port}")
            await self.background_wire_poller(interval_seconds=interval_seconds, monitored_tickers=monitored_tickers)

def main():
    server = NewsWebSocketServer(host="127.0.0.1", port=8765)
    asyncio.run(server.start_server(interval_seconds=60))

if __name__ == "__main__":
    main()
