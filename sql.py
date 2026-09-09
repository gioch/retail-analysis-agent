import json
import os
import warnings

import sqlglot
from sqlglot import exp

from langchain.messages import SystemMessage, HumanMessage

from bq_client import BigQueryRunner
from bq_schema import schema
from reports import db
import llm
from prompts import sql_generation_prompt

MAX_ROWS = 1000
# MAX_BYTES = 1 * 1024**3 # to be used in prod
# QUERY_TIMEOUT = 60 # to be used in prod
INLINE_ROWS = 50
MAX_ATTEMPTS = 3
PREVIEW_ROWS = 15

warnings.filterwarnings("ignore", message="BigQuery Storage module not found")  # REST is fine for LIMIT 1000
bq = BigQueryRunner(project_id=os.getenv("GOOGLE_BIG_QUERY_PROJECT_ID"))
results: dict[str, dict] = {}

db.execute("""
  CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY,
    result_id TEXT NOT NULL,
    intent TEXT NOT NULL,
    sql TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    snapshot TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
  )
""")


class SqlRejected(Exception):
  pass


def validate(sql: str) -> str:
  """Reject unsafe SQL, otherwise return it qualified and row-limited."""
  try:
    statements = sqlglot.parse(sql, read="bigquery")
  except sqlglot.errors.ParseError as e:
    raise SqlRejected(f"Syntax error: {e}")

  if len(statements) != 1:
    raise SqlRejected("Exactly one statement is allowed; remove the extra statements.")

  query = statements[0]
  if not isinstance(query, exp.Select):
    raise SqlRejected(f"Only SELECT is allowed, got {query.key.upper()}.")

  for select in query.find_all(exp.Select):
    for item in select.expressions:
      if isinstance(item, exp.Star) or (isinstance(item, exp.Column) and isinstance(item.this, exp.Star)):
        raise SqlRejected("SELECT * is not allowed; list the columns explicitly.")

  tables = {name: t for name, t in schema.tables.items() if t.enabled}
  allowed = {c for t in tables.values() for c, col in t.columns.items() if col.allowed}
  blocked = {c for t in tables.values() for c, col in t.columns.items() if not col.allowed}
  local_names = {a.alias for a in query.find_all(exp.Alias, exp.CTE)}

  for table in query.find_all(exp.Table):
    if table.name not in tables and table.name not in local_names:
      raise SqlRejected(f"Unknown table '{table.name}'. Available tables: {', '.join(sorted(tables))}.")

  for column in query.find_all(exp.Column):
    if column.name in blocked:
      raise SqlRejected(f"Column '{column.name}' is not available; remove it from the query.")
    if column.name not in allowed and column.name not in local_names:
      raise SqlRejected(f"Unknown column '{column.name}'. Check the table description for available columns.")

  catalog, db = schema.dataset.split(".")
  for table in query.find_all(exp.Table):
    if table.name in tables:
      table.set("catalog", exp.to_identifier(catalog))
      table.set("db", exp.to_identifier(db))

  limit = query.args.get("limit")
  if limit is None or int(limit.expression.this) > MAX_ROWS:
    query = query.limit(MAX_ROWS)

  return query.sql(dialect="bigquery")


def execute(intent: str, sql: str) -> dict:
  """Run validated SQL, keep the full result in the registry, return the envelope."""
  df = bq.execute_query(sql)
  result_id = f"r{len(results) + 1}"
  shown = df if len(df) <= INLINE_ROWS else df.head(PREVIEW_ROWS)

  envelope = {
    "ok": True,
    "result_id": result_id,
    "intent": intent,
    "sql": sql,
    "row_count": len(df),
    "columns": list(df.columns),
    "rows": json.loads(shown.to_json(orient="records", date_format="iso")),
    "truncated": len(df) > INLINE_ROWS,
  }
  results[result_id] = {**envelope, "df": df}
  # SQL is the recipe, the snapshot is the evidence: warehouse data drifts daily
  db.execute(
    "INSERT INTO results (result_id, intent, sql, row_count, snapshot) VALUES (?, ?, ?, ?, ?)",
    (result_id, intent, sql, len(df), df.to_json(orient="records", date_format="iso")),
  )
  db.commit()
  return envelope


def generate(intent: str, tables: list[str], last_error: str | None) -> str:
  user = f"Step: {intent}"
  if last_error:
    user += f"\n\nYour previous query was rejected: {last_error}\nWrite a corrected query."

  reply = llm.invoke([SystemMessage(content=sql_generation_prompt(tables)), HumanMessage(content=user)])
  return reply.content.strip().removeprefix("```sql").removeprefix("```").removesuffix("```").strip()
