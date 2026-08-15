#!/usr/bin/env python3
"""
CFA Knowledge Base Query Utility
Searches indexed CFA Level I, II, and III topics, formulas, and arXiv academic research.
"""

import sys
import sqlite3
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "cfa_knowledge_base.sqlite"

def sanitize_term(term: str) -> str:
    # Remove FTS5 operator characters
    return re.sub(r'[\*\+\-\^\:\"\(\)]', ' ', term).strip()

def search_kb(query: str, level: str = None, topic: str = None, limit: int = 5):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    clean_q = sanitize_term(query)
    words = [f'"{w}"' for w in clean_q.split() if len(w) > 1]
    if not words:
        return []
        
    fts_query = " OR ".join(words)
    
    sql = """
    SELECT ki.id, ki.level, ki.topic, ki.subtopic, ki.formulas,
           snippet(knowledge_fts, 3, '【', '】', '...', 25) as snippet,
           ki.content,
           bm25(knowledge_fts) as rank
    FROM knowledge_fts
    JOIN knowledge_items ki ON knowledge_fts.rowid = ki.id
    WHERE knowledge_fts MATCH ?
    """
    params = [fts_query]
    
    if level:
        sql += " AND ki.level LIKE ?"
        params.append(f"%{level}%")
    if topic:
        sql += " AND ki.topic LIKE ?"
        params.append(f"%{topic}%")
        
    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)
    
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return rows
    except Exception as e:
        like_sql = """
        SELECT id, level, topic, subtopic, formulas, substr(content, 1, 200) as snippet, content, 0 as rank
        FROM knowledge_items
        WHERE content LIKE ? OR subtopic LIKE ?
        LIMIT ?
        """
        cursor.execute(like_sql, [f"%{query}%", f"%{query}%", limit])
        return cursor.fetchall()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 query_cfa_kb.py <search_query>")
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    print(f"Searching CFA & Research Knowledge Base for: '{query}'...")
    results = search_kb(query, limit=5)
    
    if not results:
        print("No matches found.")
        return
        
    for i, r in enumerate(results, 1):
        print(f"\n[{i}] {r['level']} | {r['topic']} -> {r['subtopic']}")
        if r['formulas']:
            print(f"    Key Focus/Formulas: {r['formulas']}")
        print(f"    Excerpt: {r['snippet']}")
        print("-" * 60)

if __name__ == "__main__":
    main()
