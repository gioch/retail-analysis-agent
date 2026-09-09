import json
import sqlite3
from datetime import datetime, timezone

DB_PATH = "data/app.db"

db = sqlite3.connect(DB_PATH, check_same_thread=False)  # tools run in LangGraph worker threads
db.row_factory = sqlite3.Row
db.execute("""
  CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    result_ids TEXT NOT NULL,
    created_at TEXT NOT NULL,
    deleted_at TEXT
  )
""")


def save_report_row(owner_id: str, title: str, body: str, result_ids: list[str]) -> int:
  now = datetime.now(timezone.utc).isoformat(timespec="seconds")
  cursor = db.execute(
    "INSERT INTO reports (owner_id, title, body, result_ids, created_at) VALUES (?, ?, ?, ?, ?)",
    (owner_id, title, body, json.dumps(result_ids), now),
  )
  db.commit()
  return cursor.lastrowid


def list_reports(owner_id: str) -> list[sqlite3.Row]:
  return db.execute(
    "SELECT id, title, created_at FROM reports WHERE owner_id = ? AND deleted_at IS NULL ORDER BY id",
    (owner_id,),
  ).fetchall()
