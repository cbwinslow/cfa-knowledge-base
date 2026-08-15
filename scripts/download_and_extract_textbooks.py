#!/usr/bin/env python3
"""
Bulk CFA & Finance Textbook Ingestor
Downloads full-length open-access CFA monographs, open textbooks, and parses them with PyMuPDF/pypdf.
"""

import os
import sys
import sqlite3
import re
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "data" / "downloads" / "textbooks"
DB_PATH = BASE_DIR / "data" / "cfa_knowledge_base.sqlite"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Direct open-access full-length monographs and textbooks
BOOKS = [
    {
        "title": "Artificial Intelligence in Asset Management (CFA Research Foundation)",
        "url": "https://rpc.cfainstitute.org/-/media/documents/book/rf-publication/2020/artificial-intelligence-in-asset-management.pdf",
        "level": "All Levels",
        "topic": "Quantitative Methods & AI in Asset Management",
        "filename": "cfa_ai_in_asset_management.pdf"
    },
    {
        "title": "A Comprehensive Guide to Exchange-Traded Funds (CFA Research Foundation)",
        "url": "https://rpc.cfainstitute.org/-/media/documents/book/rf-publication/2015/rf-v2015-n3-1-pdf.pdf",
        "level": "Level II & III",
        "topic": "Portfolio Management & ETFs",
        "filename": "cfa_etf_guide.pdf"
    },
    {
        "title": "Guidance and Case Studies for ESG Integration (CFA Institute)",
        "url": "https://www.cfainstitute.org/-/media/documents/survey/guidance-case-studies-esg-integration.pdf",
        "level": "Level I, II, III",
        "topic": "Equity & Fixed Income ESG Integration",
        "filename": "cfa_esg_guidance.pdf"
    }
]

def download_book(url: str, dest_path: Path) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 10000:
        print(f"File already exists: {dest_path.name}")
        return True
        
    print(f"Downloading: {dest_path.name} from {url}...")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            with open(dest_path, "wb") as f:
                f.write(content)
        print(f"  ✓ Saved {dest_path.name} ({len(content):,} bytes)")
        return True
    except Exception as e:
        print(f"  ✗ Failed to download {dest_path.name}: {e}")
        return False

def extract_pdf_chunks(pdf_path: Path, max_pages: int = 150):
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        chunks = []
        for page_num in range(min(len(doc), max_pages)):
            page = doc[page_num]
            text = page.get_text()
            if len(text.strip()) > 100:
                chunks.append({
                    "page": page_num + 1,
                    "text": text.strip()
                })
        return chunks
    except Exception as e:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(pdf_path))
            chunks = []
            for i in range(min(len(reader.pages), max_pages)):
                text = reader.pages[i].extract_text()
                if text and len(text.strip()) > 100:
                    chunks.append({
                        "page": i + 1,
                        "text": text.strip()
                    })
            return chunks
        except Exception as e2:
            print(f"Error parsing {pdf_path}: {e2}")
            return []

def index_book(conn: sqlite3.Connection, book_meta: dict, pdf_path: Path):
    chunks = extract_pdf_chunks(pdf_path)
    if not chunks:
        return 0
        
    cursor = conn.cursor()
    count = 0
    for ch in chunks:
        content = ch["text"]
        page_num = ch["page"]
        subtopic = f"{book_meta['title']} (Page {page_num})"
        
        formulas = []
        for line in content.split("\n"):
            if re.search(r'(=|\\frac|WACC|CAPM|Sharpe|Sortino|MVO|Black-Litterman|DCF|FCFF|FCFE|Duration|Alpha|Beta)', line):
                if len(line.strip()) < 200 and len(line.strip()) > 5:
                    formulas.append(line.strip())
        formulas_str = "\n".join(formulas[:8])
        
        cursor.execute("""
        INSERT INTO knowledge_items (level, topic, subtopic, source_file, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (book_meta["level"], book_meta["topic"], subtopic, pdf_path.name, content, formulas_str, book_meta["title"]))
        
        item_id = cursor.lastrowid
        cursor.execute("""
        INSERT INTO knowledge_fts (rowid, level, topic, subtopic, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_id, book_meta["level"], book_meta["topic"], subtopic, content, formulas_str, book_meta["title"]))
        
        count += 1
        
    conn.commit()
    return count

def main():
    print("==================================================")
    print("Bulk PDF Textbook & Monograph Ingestion")
    print("==================================================")
    conn = sqlite3.connect(DB_PATH)
    
    total_added = 0
    for book in BOOKS:
        dest = DOWNLOADS_DIR / book["filename"]
        success = download_book(book["url"], dest)
        if success and dest.exists():
            added = index_book(conn, book, dest)
            print(f"  -> Indexed {added} pages from {dest.name}")
            total_added += added
            
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM knowledge_items;")
    total_items = cursor.fetchone()[0]
    
    print("\n==================================================")
    print(f"Ingestion Complete! Added {total_added} pages.")
    print(f"Total Knowledge Base Items: {total_items}")
    print("==================================================")

if __name__ == "__main__":
    main()
