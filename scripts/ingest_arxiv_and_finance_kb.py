#!/usr/bin/env python3
"""
arXiv Quantitative Finance & Economics + Financial Formulas Ingestion Pipeline
Fetches seminal & recent papers from arXiv (q-fin.PM, q-fin.RM, q-fin.PR, econ.EM, econ.GN)
and structures them into the CFA Knowledge Base.
"""

import os
import sys
import sqlite3
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import time
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cfa_knowledge_base.sqlite"

ARXIV_QUERIES = [
    {"topic": "Quantitative Portfolio Management & Black-Litterman", "query": "cat:q-fin.PM AND (all:asset allocation OR all:portfolio optimization OR all:Black-Litterman)"},
    {"topic": "Risk Management, VaR & Factor Models", "query": "cat:q-fin.RM AND (all:VaR OR all:CVaR OR all:factor model OR all:stress testing)"},
    {"topic": "Asset Pricing & Equity Valuation", "query": "cat:q-fin.PR AND (all:valuation OR all:asset pricing OR all:discounted cash flow OR all:equity premium)"},
    {"topic": "Econometrics & Time Series Modeling", "query": "cat:econ.EM AND (all:time series OR all:volatility OR all:GARCH OR all:yield curve)"},
    {"topic": "Machine Learning & Neural Asset Pricing", "query": "cat:q-fin.ST AND (all:machine learning OR all:deep learning OR all:ensemble)"},
    {"topic": "Macroeconomics & Monetary Economics", "query": "cat:econ.GN AND (all:inflation OR all:interest rates OR all:monetary policy)"}
]

def fetch_arxiv_papers(search_query: str, max_results: int = 40):
    base_url = "http://export.arxiv.org/api/query?"
    params = {
        "search_query": search_query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }
    url = base_url + urllib.parse.urlencode(params)
    print(f"Querying arXiv API: {search_query} (Max: {max_results})...")
    
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CFA-Quant-Engine/1.0 (academic-research)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
            summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")
            published = entry.find("atom:published", ns).text[:10] if entry.find("atom:published", ns) is not None else ""
            arxiv_id = entry.find("atom:id", ns).text if entry.find("atom:id", ns) is not None else ""
            
            authors = []
            for author in entry.findall("atom:author", ns):
                name = author.find("atom:name", ns).text
                if name:
                    authors.append(name)
            authors_str = ", ".join(authors[:4])
            
            papers.append({
                "title": title,
                "summary": summary,
                "published": published,
                "authors": authors_str,
                "arxiv_id": arxiv_id
            })
        print(f"  ✓ Fetched {len(papers)} papers from arXiv.")
        return papers
    except Exception as e:
        print(f"  ✗ arXiv API error: {e}")
        return []

def index_arxiv_papers(conn: sqlite3.Connection, topic_meta: dict, papers: list):
    cursor = conn.cursor()
    count = 0
    for p in papers:
        subtopic = f"{p['title']} ({p['published']})"
        content = f"Title: {p['title']}\nAuthors: {p['authors']}\nPublished: {p['published']}\nArXiv Link: {p['arxiv_id']}\n\nAbstract:\n{p['summary']}"
        
        formulas = []
        for line in p['summary'].split(". "):
            if re.search(r'(portfolio|return|variance|volatility|alpha|beta|factor|equilibrium|estimation|optimization)', line, re.IGNORECASE):
                formulas.append(line.strip())
        formulas_str = "; ".join(formulas[:3])
        
        cursor.execute("""
        INSERT INTO knowledge_items (level, topic, subtopic, source_file, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("Academic Research", topic_meta["topic"], subtopic, "arXiv Academic Feed", content, formulas_str, f"{topic_meta['topic']} {p['title']}"))
        
        item_id = cursor.lastrowid
        cursor.execute("""
        INSERT INTO knowledge_fts (rowid, level, topic, subtopic, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_id, "Academic Research", topic_meta["topic"], subtopic, content, formulas_str, f"{topic_meta['topic']} {p['title']}"))
        
        count += 1
        
    conn.commit()
    return count

def main():
    print("==================================================")
    print("Ingesting arXiv Quantitative Finance & Econ Papers")
    print("==================================================")
    conn = sqlite3.connect(DB_PATH)
    
    total_added = 0
    for item in ARXIV_QUERIES:
        papers = fetch_arxiv_papers(item["query"], max_results=35)
        if papers:
            added = index_arxiv_papers(conn, item, papers)
            print(f"  -> Indexed {added} papers for {item['topic']}")
            total_added += added
        time.sleep(1.5)  # Be polite to arXiv rate limits
        
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM knowledge_items;")
    grand_total = cursor.fetchone()[0]
    
    print("\n==================================================")
    print(f"Ingestion Finished! Total arXiv Papers Added: {total_added}")
    print(f"Grand Total Knowledge Base Items: {grand_total}")
    print("==================================================")

if __name__ == "__main__":
    main()
