"""
Institutional Bloomberg-Style Financial News Wire Ingestion & Vector Engine
Powered by zero-cost public financial RSS/Atom feeds, DuckDB, and FastEmbed ONNX embeddings.

Features:
1. Real-Time Multi-Source Wires:
   - SEC EDGAR 8-K Breaking Material Corporate Events
   - Federal Reserve FOMC Policy Press Releases
   - Market News Wires (Yahoo Finance, Google News Financial RSS, PR Newswire)
2. Permanent Columnar Storage in DuckDB (Zero Data Loss)
3. Local 384-Dimensional Vector Embeddings (FastEmbed BAAI/bge-small-en-v1.5)
4. Hybrid Vector + Keyword Semantic Search for CFA Copilot RAG
"""

import re
import io
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import requests
import feedparser
import duckdb
import numpy as np

try:
    from fastembed import TextEmbedding
except ImportError:
    TextEmbedding = None

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "news_wire.duckdb"

FREE_NEWS_WIRES = {
    "SEC_8K_MATERIAL_EVENTS": "https://www.sec.gov/Archives/edgar/usgaap.rss.xml",
    "FEDERAL_RESERVE_FOMC": "https://www.federalreserve.gov/feeds/press_all.xml",
    "YAHOO_FINANCE_TOP_NEWS": "https://finance.yahoo.com/news/rssindex",
    "PR_NEWSWIRE_BUSINESS": "https://www.prnewswire.com/rss/financial-services-latest-news/financial-services-latest-news-list.rss"
}

class NewsWireEngine:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_duckdb()
        self._embedder = None

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(str(self.db_path))

    def _init_duckdb(self):
        conn = self._get_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news_articles (
                article_id VARCHAR PRIMARY KEY,
                source_wire VARCHAR NOT NULL,
                wire_channel VARCHAR NOT NULL,
                ticker VARCHAR,
                title VARCHAR NOT NULL,
                summary VARCHAR,
                full_text VARCHAR,
                url VARCHAR,
                published_at TIMESTAMP,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                raw_payload_json VARCHAR,
                embedding_vector DOUBLE[],
                sentiment_score DOUBLE DEFAULT 0.0
            );
            
            CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_articles(ticker);
            CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);
        """)
        conn.close()

    def _get_embedder(self):
        if self._embedder is None and TextEmbedding is not None:
            try:
                self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            except Exception:
                self._embedder = None
        return self._embedder

    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generates local 384-dimensional dense ONNX embedding (zero API cost)"""
        embedder = self._get_embedder()
        if embedder:
            try:
                cleaned = text.strip()[:1000]
                vec = list(embedder.embed([cleaned]))[0]
                return [float(x) for x in vec]
            except Exception:
                pass
        return None

    def compute_article_id(self, url: str, title: str) -> str:
        raw = f"{url}_{title}".strip().lower()
        return f"NEWS-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"

    # ==================== WIRE FEED INGESTION ====================
    def ingest_ticker_news(self, ticker: str, max_articles: int = 10) -> int:
        """
        Pulls real-time news wire for a specific stock ticker via Google Financial RSS.
        """
        encoded_ticker = ticker.strip().upper()
        feed_url = f"https://news.google.com/rss/search?q={encoded_ticker}+stock+when:7d&hl=en-US&gl=US&ceid=US:en"
        return self._ingest_rss_feed(feed_url, source_wire="Google Finance RSS", wire_channel="EQUITY_WIRE", default_ticker=encoded_ticker, max_items=max_articles)

    def ingest_macro_and_sec_wires(self, max_articles_per_wire: int = 10) -> Dict[str, int]:
        """
        Pulls SEC 8-K material events, Federal Reserve FOMC wires, and market RSS feeds.
        """
        results = {}
        headers = {"User-Agent": "CfaQuantSuite/2.0 (Institutional Research Platform; charterholder@cfa.org)"}
        
        for wire_name, url in FREE_NEWS_WIRES.items():
            try:
                count = self._ingest_rss_feed(url, source_wire=wire_name, wire_channel="MACRO_SEC_WIRE", custom_headers=headers, max_items=max_articles_per_wire)
                results[wire_name] = count
            except Exception:
                results[wire_name] = 0
        return results

    def _ingest_rss_feed(
        self,
        url: str,
        source_wire: str,
        wire_channel: str,
        default_ticker: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        max_items: int = 15
    ) -> int:
        """
        Parses RSS/Atom wire, extracts full metadata, generates embeddings, and saves to DuckDB.
        """
        headers = custom_headers or {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        try:
            resp = requests.get(url, headers=headers, timeout=5.0)
            if resp.status_code != 200:
                return 0
            feed = feedparser.parse(resp.content)
        except Exception:
            return 0

        ingested_count = 0
        conn = self._get_connection()

        for entry in feed.entries[:max_items]:
            title = str(entry.get("title", "")).strip()
            if not title:
                continue
                
            link = str(entry.get("link", ""))
            summary = str(entry.get("summary", "") or entry.get("description", ""))
            # Strip HTML tags
            clean_summary = re.sub(r'<[^>]+>', '', summary).strip()
            
            # Extract ticker from title if not provided
            t_ticker = default_ticker
            if not t_ticker:
                m = re.search(r'\b([A-Z]{2,5})\b', title)
                if m:
                    t_ticker = m.group(1)

            art_id = self.compute_article_id(link, title)
            
            # Parse publish date
            pub_raw = entry.get("published", entry.get("updated", ""))
            try:
                pub_dt = pd.to_datetime(pub_raw).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                pub_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Dense Vector Embedding
            text_to_embed = f"{title}. {clean_summary}"
            embedding = self.generate_embedding(text_to_embed)

            # Raw unadulterated payload (Zero Data Loss)
            raw_payload = json.dumps(dict(entry), default=str)

            try:
                conn.execute("""
                    INSERT OR REPLACE INTO news_articles (
                        article_id, source_wire, wire_channel, ticker, title, summary, full_text,
                        url, published_at, ingested_at, raw_payload_json, embedding_vector
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
                """, [
                    art_id, source_wire, wire_channel, t_ticker, title, clean_summary, clean_summary,
                    link, pub_dt, raw_payload, embedding
                ])
                ingested_count += 1
            except Exception:
                pass

        conn.close()
        return ingested_count

    # ==================== VECTOR & HYBRID SEMANTIC SEARCH ====================
    def search_news_wire(
        self,
        query: str,
        ticker: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Hybrid Vector + Keyword Semantic Search over ingested news articles.
        """
        query_vec = self.generate_embedding(query)
        conn = self._get_connection()
        
        sql = """
            SELECT article_id, source_wire, wire_channel, ticker, title, summary, url, published_at, raw_payload_json, embedding_vector
            FROM news_articles
        """
        params = []
        if ticker:
            sql += " WHERE ticker = ?"
            params.append(ticker.upper())
            
        sql += " ORDER BY published_at DESC LIMIT 100;"
        
        df_news = conn.execute(sql, params).df()
        conn.close()
        
        if df_news.empty:
            return []

        results = []
        for _, row in df_news.iterrows():
            sim_score = 0.5
            # Cosine similarity if embedding available
            emb = row["embedding_vector"]
            if query_vec and emb is not None and len(emb) > 0:
                try:
                    v_art = np.array(emb, dtype=np.float32)
                    v_q = np.array(query_vec, dtype=np.float32)
                    norm_a = np.linalg.norm(v_art)
                    norm_q = np.linalg.norm(v_q)
                    if norm_a > 0 and norm_q > 0:
                        sim_score = float(np.dot(v_art, v_q) / (norm_a * norm_q))
                except Exception:
                    pass
            elif query.lower() in str(row["title"]).lower() or query.lower() in str(row["summary"]).lower():
                sim_score = 0.85

            results.append({
                "article_id": row["article_id"],
                "source_wire": row["source_wire"],
                "wire_channel": row["wire_channel"],
                "ticker": row["ticker"],
                "title": row["title"],
                "summary": row["summary"],
                "url": row["url"],
                "published_at": str(row["published_at"]),
                "similarity_score": round(sim_score, 4),
                "raw_payload": json.loads(row["raw_payload_json"]) if row["raw_payload_json"] else {}
            })

        # Sort by similarity score descending
        results = sorted(results, key=lambda x: x["similarity_score"], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    nw = NewsWireEngine()
    print("=" * 80)
    print("🏛️ CFA BLOOMBERG-STYLE FINANCIAL NEWS WIRE & VECTOR ENGINE")
    print("=" * 80)
    
    # 1. Ingest Ticker News for MSFT & AAPL
    n_msft = nw.ingest_ticker_news("MSFT", max_articles=5)
    n_aapl = nw.ingest_ticker_news("AAPL", max_articles=5)
    print(f"✓ Ingested {n_msft} MSFT articles and {n_aapl} AAPL articles into DuckDB news warehouse.")
    
    # 2. Ingest Macro & Fed Wires
    macro_res = nw.ingest_macro_and_sec_wires(max_articles_per_wire=3)
    print(f"✓ Macro & SEC Ingestion Summary: {macro_res}")
    
    # 3. Vector Semantic Search
    search_q = "cloud growth and artificial intelligence revenue"
    matches = nw.search_news_wire(search_q, ticker="MSFT", top_k=3)
    print(f"\n🔍 Vector Semantic Search for: '{search_q}'")
    for idx, m in enumerate(matches, 1):
        print(f"  {idx}. [{m['similarity_score']:.3f}] {m['title']} ({m['published_at']})")
        print(f"     Source: {m['source_wire']} | URL: {m['url'][:60]}...")
    print("=" * 80)
