#!/usr/bin/env python3
"""
Knowledge Base Pruner, Deduplicator & Optimizer
Scans SQLite database, removes noise/boilerplate, deduplicates identical chunks,
and rebuilds the FTS5 index for peak query performance.
"""

import sqlite3
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cfa_knowledge_base.sqlite"

def prune_and_optimize():
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    cursor = conn.cursor()
    
    print("Scanning database for duplicates and noise...")
    cursor.execute("SELECT id, content FROM knowledge_items;")
    rows = cursor.fetchall()
    
    seen_hashes = set()
    to_delete = []
    
    for row_id, content in rows:
        clean_text = content.strip()
        if len(clean_text) < 60:
            to_delete.append(row_id)
            continue
            
        text_hash = hashlib.md5(clean_text[:500].encode('utf-8')).hexdigest()
        if text_hash in seen_hashes:
            to_delete.append(row_id)
        else:
            seen_hashes.add(text_hash)
            
    print(f"Found {len(to_delete)} duplicate/low-value items to prune.")
    
    if to_delete:
        cursor.execute("BEGIN TRANSACTION;")
        for chunk_start in range(0, len(to_delete), 500):
            batch = to_delete[chunk_start:chunk_start+500]
            cursor.execute(f"DELETE FROM knowledge_items WHERE id IN ({','.join(['?']*len(batch))});", batch)
        cursor.execute("COMMIT;")
        
    print("Rebuilding FTS5 full-text index...")
    cursor.execute("DROP TABLE IF EXISTS knowledge_fts;")
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
    cursor.execute("""
    INSERT INTO knowledge_fts (rowid, level, topic, subtopic, content, formulas, key_terms)
    SELECT id, level, topic, subtopic, content, formulas, key_terms FROM knowledge_items;
    """)
    
    cursor.execute("VACUUM;")
    
    cursor.execute("SELECT COUNT(*) FROM knowledge_items;")
    final_count = cursor.fetchone()[0]
    
    print(f"✓ Optimization Complete! Cleaned high-quality knowledge items: {final_count}")
    return final_count

if __name__ == "__main__":
    prune_and_optimize()
