import json
import sqlite3
from datetime import datetime, timezone

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

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


@tool
def save_report(title: str, body: str, result_ids: list[str], config: RunnableConfig) -> dict:
  """Save the analysis as a report in the user's library. Call this when the user asks for
  a report or asks to save the analysis. Pass a short title, the full report text in markdown,
  and the result_ids of the query results the report is based on."""
  owner_id = config["configurable"]["user_id"]
  now = datetime.now(timezone.utc).isoformat(timespec="seconds")
  cursor = db.execute(
    "INSERT INTO reports (owner_id, title, body, result_ids, created_at) VALUES (?, ?, ?, ?, ?)",
    (owner_id, title, body, json.dumps(result_ids), now),
  )
  db.commit()
  return {"ok": True, "report_id": cursor.lastrowid, "title": title}


def list_reports(owner_id: str) -> list[sqlite3.Row]:
  return db.execute(
    "SELECT id, title, created_at FROM reports WHERE owner_id = ? AND deleted_at IS NULL ORDER BY id",
    (owner_id,),
  ).fetchall()
