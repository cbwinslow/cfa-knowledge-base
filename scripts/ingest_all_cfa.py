#!/usr/bin/env python3
"""
Comprehensive CFA Knowledge Base Ingestor
Recursively parses Level I, II, and III markdown, text, and notes from downloaded curriculum repositories
and indexes them into SQLite FTS5 for fast semantic and keyword search.
"""

import os
import sys
import json
import sqlite3
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "data" / "downloads"
DB_PATH = BASE_DIR / "data" / "cfa_knowledge_base.sqlite"

def init_database(db_file: Path):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS knowledge_fts;")
    cursor.execute("DROP TABLE IF EXISTS knowledge_items;")
    
    cursor.execute("""
    CREATE TABLE knowledge_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT,
        topic TEXT,
        subtopic TEXT,
        source_file TEXT,
        content TEXT,
        formulas TEXT,
        key_terms TEXT
    );
    """)
    cursor.execute("""
    CREATE VIRTUAL TABLE knowledge_fts USING fts5(
        level,
        topic,
        subtopic,
        content,
        formulas,
        key_terms,
        content=knowledge_items,
        content_rowid=id
    );
    """)
    conn.commit()
    return conn

def detect_level_and_topic(file_path: Path):
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
        "privatewealth": "Private Wealth Management",
        "assetallocation": "Asset Allocation & Portfolio Planning",
        "asset allocation": "Asset Allocation & Portfolio Planning",
        "equity": "Equity Valuation",
        "fixed": "Fixed Income",
        "financial statement": "Financial Statement Analysis",
        "derivatives": "Derivatives & Risk Management",
        "alternative": "Alternative Investments",
        "institutional": "Institutional Portfolio Management",
        "behavior": "Behavioral Finance",
        "ethics": "Ethics & Professional Standards",
        "quant": "Quantitative Methods",
        "economic": "Economics",
        "corporate": "Corporate Issuers / Corporate Finance"
    }
    
    for key, val in topic_mappings.items():
        if key in path_str:
            topic = val
            break
            
    return level, topic

def extract_formulas(text: str) -> str:
    lines = text.split("\n")
    formulas = []
    for line in lines:
        if re.search(r'(=|\\frac|WACC|CAPM|Sharpe|Sortino|Treynor|MVO|Black-Litterman|DCF|FCFF|FCFE|DuPont|Piotroski|Beneish|Duration|Convexity|IPS|Human Capital)', line, re.IGNORECASE):
            if len(line.strip()) < 200 and len(line.strip()) > 5:
                formulas.append(line.strip())
    return "\n".join(formulas[:8])

def ingest_all(conn: sqlite3.Connection):
    cursor = conn.cursor()
    total_files = 0
    total_chunks = 0
    
    extensions = [".md", ".markdown", ".txt", ".rst", ".json"]
    
    for root, dirs, files in os.walk(DOWNLOADS_DIR):
        if ".git" in root:
            continue
        for file in files:
            p = Path(root) / file
            if p.suffix.lower() in extensions:
                total_files += 1
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception as e:
                    continue
                
                if len(text.strip()) < 40:
                    continue
                
                level, topic = detect_level_and_topic(p)
                
                # Split content into readable chunks
                chunks = re.split(r'\n(?=#{1,3}\s+)', text) if p.suffix.lower() in [".md", ".markdown"] else [text[i:i+3000] for i in range(0, len(text), 2500)]
                
                for chunk in chunks:
                    chunk = chunk.strip()
                    if len(chunk) < 50:
                        continue
                    
                    lines = chunk.split("\n")
                    header_match = re.match(r'^#{1,3}\s+(.+)$', lines[0])
                    subtopic = header_match.group(1).strip() if header_match else p.stem.replace("_", " ").title()
                    
                    formulas = extract_formulas(chunk)
                    
                    cursor.execute("""
                    INSERT INTO knowledge_items (level, topic, subtopic, source_file, content, formulas, key_terms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (level, topic, subtopic, p.name, chunk, formulas, f"{topic} {subtopic}"))
                    
                    item_id = cursor.lastrowid
                    cursor.execute("""
                    INSERT INTO knowledge_fts (rowid, level, topic, subtopic, content, formulas, key_terms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (item_id, level, topic, subtopic, chunk, formulas, f"{topic} {subtopic}"))
                    
                    total_chunks += 1
                    
    conn.commit()
    return total_files, total_chunks

def main():
    print("==================================================")
    print("Indexing CFA Multi-Level Curriculum Knowledge Base")
    print("==================================================")
    conn = init_database(DB_PATH)
    files_count, chunks_count = ingest_all(conn)
    print(f"Processed {files_count} files.")
    print(f"Successfully indexed {chunks_count} structured knowledge units across Levels I, II, and III!")
    print(f"Database ready at: {DB_PATH}")

if __name__ == "__main__":
    main()
