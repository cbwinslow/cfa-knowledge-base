#!/usr/bin/env python3
"""
CFA Knowledge Base Downloader & Structuring Pipeline
Automatically downloads open-access CFA formula sheets, topic summaries (Levels I, II, III),
and open research monographs, structuring them into searchable JSON and SQLite FTS5 database.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "data" / "downloads"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "data" / "cfa_knowledge_base.sqlite"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Curated open-source CFA repositories and reference formula sheets
OPEN_SOURCES = [
    {
        "name": "cfa_formula_sheets",
        "url": "https://raw.githubusercontent.com/arminv/CFA-Formula-Sheets/master/README.md",
        "topic": "Formulas & Equations",
        "level": "All Levels",
        "filename": "cfa_formula_sheet_arminv.md"
    },
    {
        "name": "cfa_level1_prep_guide",
        "url": "https://raw.githubusercontent.com/start-again-06/Chartered-Financial-Analyst---Preparation-Guide/main/README.md",
        "topic": "Comprehensive Curriculum Guide",
        "level": "Level I",
        "filename": "cfa_level1_guide.md"
    },
    {
        "name": "cfa_frm_study_notes",
        "url": "https://raw.githubusercontent.com/qiaoliangxiang/cfa/master/README.md",
        "topic": "Quant & Risk Management",
        "level": "Level I & II",
        "filename": "cfa_frm_notes.md"
    }
]

def download_file(url: str, dest_path: Path) -> bool:
    print(f"Downloading: {url} -> {dest_path.name}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
            with open(dest_path, "wb") as f:
                f.write(content)
        print(f"  ✓ Saved ({len(content):,} bytes)")
        return True
    except Exception as e:
        print(f"  ✗ Failed to download {url}: {e}")
        return False

def init_database(db_file: Path):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT,
        topic TEXT,
        subtopic TEXT,
        source TEXT,
        content TEXT,
        formulas TEXT,
        key_terms TEXT
    );
    """)
    cursor.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
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

def parse_and_index_markdown(conn: sqlite3.Connection, file_path: Path, source_meta: dict):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    cursor = conn.cursor()
    sections = re.split(r'\n(?=#{1,3}\s+)', text)
    
    indexed_count = 0
    for sec in sections:
        sec = sec.strip()
        if not sec or len(sec) < 50:
            continue
        
        lines = sec.split("\n")
        header_match = re.match(r'^#{1,3}\s+(.+)$', lines[0])
        subtopic = header_match.group(1).strip() if header_match else "General"
        
        formulas = []
        for line in lines:
            if re.search(r'[\$\\=]|CAGR|WACC|CAPM|Sharpe|DuPont|FCFF|FCFE|Duration|Convexity', line):
                formulas.append(line.strip())
        
        formulas_str = "\n".join(formulas[:10])
        
        cursor.execute("""
        INSERT INTO knowledge_items (level, topic, subtopic, source, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            source_meta.get("level", "All Levels"),
            source_meta.get("topic", "General"),
            subtopic,
            source_meta.get("name", file_path.name),
            sec,
            formulas_str,
            subtopic
        ))
        
        item_id = cursor.lastrowid
        cursor.execute("""
        INSERT INTO knowledge_fts (rowid, level, topic, subtopic, content, formulas, key_terms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            item_id,
            source_meta.get("level", "All Levels"),
            source_meta.get("topic", "General"),
            subtopic,
            sec,
            formulas_str,
            subtopic
        ))
        indexed_count += 1
        
    conn.commit()
    print(f"  Indexed {indexed_count} knowledge chunks from {file_path.name}")

def main():
    print("==================================================")
    print("CFA Knowledge Base Ingestion Pipeline Starting...")
    print("==================================================")
    
    conn = init_database(DB_PATH)
    
    for source in OPEN_SOURCES:
        dest = DOWNLOADS_DIR / source["filename"]
        if not dest.exists():
            download_file(source["url"], dest)
        if dest.exists():
            parse_and_index_markdown(conn, dest, source)
            
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM knowledge_items;")
    total_items = cursor.fetchone()[0]
    
    print("\n==================================================")
    print(f"Knowledge Base Ready! Total indexed chunks: {total_items}")
    print(f"Database stored at: {DB_PATH}")
    print("==================================================")

if __name__ == "__main__":
    main()
