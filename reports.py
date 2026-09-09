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
db.execute("""
  CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL
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


def find_reports(owner_id: str, mentioning: str | None = None, since: str | None = None) -> list[sqlite3.Row]:
  """Only the caller's own, non-deleted reports; ownership is a WHERE clause, never a model decision."""
  where, params = ["owner_id = ?", "deleted_at IS NULL"], [owner_id]
  if mentioning:
    where.append("(title LIKE ? OR body LIKE ?)")
    params += [f"%{mentioning}%", f"%{mentioning}%"]
  if since:
    where.append("created_at >= ?")
    params.append(since)
  return db.execute(f"SELECT id, title, created_at FROM reports WHERE {' AND '.join(where)} ORDER BY id", params).fetchall()


def soft_delete_reports(owner_id: str, ids: list[int]) -> int:
  now = datetime.now(timezone.utc).isoformat(timespec="seconds")
  placeholders = ",".join("?" * len(ids))
  cursor = db.execute(
    f"UPDATE reports SET deleted_at = ? WHERE owner_id = ? AND deleted_at IS NULL AND id IN ({placeholders})",
    [now, owner_id, *ids],
  )
  db.execute("INSERT INTO audit (actor, action, payload, created_at) VALUES (?, ?, ?, ?)",
             (owner_id, "delete_reports", json.dumps(ids), now))
  db.commit()
  return cursor.rowcount
