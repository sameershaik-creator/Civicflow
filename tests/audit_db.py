"""
Diagnostic script for Zero-Demo-Data Audit.
Inspects civicflow.db and backend/civicflow.db.
"""
import sqlite3
import os
from pathlib import Path

root = Path(__file__).resolve().parent.parent

for db_path in [root / "civicflow.db", root / "backend" / "civicflow.db"]:
    print("=" * 60)
    print(f"Inspecting: {db_path}")
    if not db_path.exists():
        print("File does not exist.")
        continue
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"Tables found: {tables}")
    
    for table in tables:
        if table.startswith("sqlite_"):
            continue
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"  Table '{table}': {count} rows")
        if count > 0:
            cursor.execute(f"SELECT * FROM {table} LIMIT 5;")
            sample_rows = cursor.fetchall()
            print(f"    Rows: {sample_rows}")
    conn.close()
