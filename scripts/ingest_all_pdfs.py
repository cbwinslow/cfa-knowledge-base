#!/usr/bin/env python3
"""
Deep PDF Ingestor for CFA Textbooks, Monographs, Topic Summaries, and Mock Exams.
Iterates across all downloaded PDF books and guides, parses text with PyMuPDF,
and indexes every page into SQLite FTS5.
"""

import os
import sys
import sqlite3
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "data" / "downloads"
DB_PATH = BASE_DIR / "data" / "cfa_knowledge_base.sqlite"

def detect_meta_from_path(file_path: Path):
    path_str = str(file_path).lower()
    
    level = "All Levels"
    if "level iii" in path_str or "level_3" in path_str or "level 3" in path_str or "l3" in path_str or "l-3" in path_str:
        level = "Level III"
    elif "level ii" in path_str or "level_2" in path_str or "level 2" in path_str or "l2" in path_str or "l-2" in path_str:
        level = "Level II"
    elif "level i" in path_str or "level_1" in path_str or "level 1" in path_str or "l1" in path_str or "l-1" in path_str:
        level = "Level I"
        
    topic = "General Finance"
    topic_mappings = {
        "wealth": "Private Wealth Management",
        "assetallocation": "Asset Allocation & Portfolio Planning",
        "equity": "Equity Valuation",
        "fixed": "Fixed Income",
        "fra": "Financial Statement Analysis",
        "financial statement": "Financial Statement Analysis",
        "derivatives": "Derivatives & Risk Management",
        "alternative": "Alternative Investments",
        "institutional": "Institutional Portfolio Management",
        "behaviour": "Behavioral Finance",
        "behavior": "Behavioral Finance",
        "ethics": "Ethics & Professional Standards",
        "ethic": "Ethics & Professional Standards",
        "trading": "Execution & Performance Evaluation",
        "quant": "Quantitative Methods",
        "economic": "Economics",
        "mock": "Mock Exams & Practice Tests",
        "formula": "Formula Sheet & Summary Charts"
    }
    
    for key, val in topic_mappings.items():
        if key in path_str:
            topic = val
            break
            
    return level, topic

def extract_and_index_pdf(conn: sqlite3.Connection, pdf_path: Path):
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
        
    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception as e:
        print(f"  ✗ Error opening {pdf_path.name}: {e}")
        return 0
        
    level, topic = detect_meta_from_path(pdf_path)
    cursor = conn.cursor()
    indexed_pages = 0
    
    # Process up to 500 pages per book
    max_pages = min(len(doc), 500)
    for page_idx in range(max_pages):
        page = doc[page_idx]
        text = page.get_text()
        if not text or len(text.strip()) < 80:
            continue
            
        page_num = page_idx + 1
        subtopic = f"{pdf_path.stem} (Page {page_num}/{len(doc)})"
        
        formulas = []
        for line in text.split("\n"):
            if re.search(r'(=|\\frac|WACC|CAPM|Sharpe|Sortino|Treynor|MVO|Black-Litterman|DCF|FCFF|FCFE|DuPont|Piotroski|Beneish|Duration|Convexity|IPS|Human Capital|Alpha|Beta|VaR|CVaR)', line, re.IGNORECASE):
                if 5 < len(line.strip()) < 200:
                    formulas.append(line.strip())
        formulas_str = "\n".join(formulas[:8])
        
        cursor.execute("""
        INSERT INTO knowledge_items (level, topic, subtopic, source_file, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (level, topic, subtopic, pdf_path.name, text.strip(), formulas_str, f"{topic} {pdf_path.stem}"))
        
        item_id = cursor.lastrowid
        cursor.execute("""
        INSERT INTO knowledge_fts (rowid, level, topic, subtopic, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_id, level, topic, subtopic, text.strip(), formulas_str, f"{topic} {pdf_path.stem}"))
        
        indexed_pages += 1
        
    conn.commit()
    return indexed_pages

def main():
    print("==================================================")
    print("Deep Scanning & Ingesting All PDF Textbooks & Exams")
    print("==================================================")
    conn = sqlite3.connect(DB_PATH)
    
    pdf_files = list(DOWNLOADS_DIR.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF books, topic reviews, formula sheets, and exams.")
    
    total_new_pages = 0
    for i, pdf in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Parsing: {pdf.name}...")
        pages = extract_and_index_pdf(conn, pdf)
        print(f"    -> Indexed {pages} pages.")
        total_new_pages += pages
        
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM knowledge_items;")
    grand_total = cursor.fetchone()[0]
    
    print("\n==================================================")
    print(f"Ingestion Finished! Total New Pages Added: {total_new_pages}")
    print(f"Grand Total Knowledge Base Items: {grand_total}")
    print("==================================================")

if __name__ == "__main__":
    main()
