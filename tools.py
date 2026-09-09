import logging

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

import sql
from preferences import OPTIONS, set_preference_value
from reports import save_report_row, find_reports, soft_delete_reports


@tool(parse_docstring=True)
def run_sql(intent: str, tables: list[str]) -> dict:
  """Run one analysis step against the database. Returns a result envelope with a
  result_id, the SQL used, row_count and rows (or a preview when there are many).

  Args:
    intent: What this step should compute, in plain English, e.g. "monthly revenue in California for 2025".
    tables: Names of the tables the step needs, from the schema catalog.
  """
  last_error = None
  for attempt in range(1, sql.MAX_ATTEMPTS + 1):
    query = sql.generate(intent, tables, last_error)
    try:
      envelope = sql.execute(intent, sql.validate(query))
      envelope["attempts"] = attempt
      sql.results[envelope["result_id"]]["attempts"] = attempt
      logging.info("run_sql ok result_id=%s rows=%s attempts=%s", envelope["result_id"], envelope["row_count"], attempt)
      return envelope
    except sql.SqlRejected as e:
      last_error = str(e)
    except Exception as e:
      last_error = f"BigQuery error: {e}"
    logging.info("run_sql retry attempt=%s error=%s", attempt, last_error[:200])

  logging.warning("run_sql failed intent=%r error=%s", intent, last_error[:200])
  return {"ok": False, "intent": intent, "last_error": last_error, "attempts": sql.MAX_ATTEMPTS}


@tool(parse_docstring=True)
def save_report(title: str, body: str, result_ids: list[str], config: RunnableConfig) -> dict:
  """Save the analysis as a report in the user's library. Call this when the user asks for
  a report or asks to save the analysis.

  Args:
    title: Short report title.
    body: The full report text in markdown, including findings and action items.
    result_ids: The result_ids of the query results the report is based on, e.g. ["r1", "r2"].
  """
  report_id = save_report_row(config["configurable"]["user_id"], title, body, result_ids)
  return {"ok": True, "report_id": report_id, "title": title}


@tool(parse_docstring=True)
def set_preference(key: str, value: str, config: RunnableConfig) -> dict:
  """Remember how the user wants answers. Call this when the user states a lasting
  preference, e.g. "always show tables" or "keep it brief".

  Args:
    key: "format" or "depth".
    value: For format one of table, bullets, prose. For depth one of headline, standard, deep.
  """
  if value not in OPTIONS.get(key, []):
    return {"ok": False, "error": f"'{key}' must be one of {OPTIONS.get(key)}"}
  set_preference_value(config["configurable"]["user_id"], key, value)
  return {"ok": True, key: value}


@tool(parse_docstring=True)
def delete_reports(config: RunnableConfig, mentioning: str | None = None, this_conversation: bool = False) -> dict:
  """Delete saved reports from the user's library. The user is asked to confirm outside of you;
  report the outcome exactly as returned.

  Args:
    mentioning: Text the report must mention, for "delete reports mentioning X".
    this_conversation: True for "delete the reports we made in this conversation".
  """
  owner_id = config["configurable"]["user_id"]
  since = config["configurable"]["session_started_at"] if this_conversation else None
  matches = find_reports(owner_id, mentioning=mentioning, since=since)
  if not matches:
    return {"ok": True, "deleted": 0, "message": "No matching reports."}

  ids = [row["id"] for row in matches]  # frozen before the pause; nothing added later can be touched
  expected = f"delete {len(ids)} report" + ("s" if len(ids) > 1 else "")
  answer = interrupt({
    "reports": [{"id": row["id"], "title": row["title"], "created_at": row["created_at"]} for row in matches],
    "expected": expected,
  })

  if str(answer).strip().lower() != expected:
    logging.info("delete_reports cancelled by user ids=%s", ids)
    return {"ok": True, "deleted": 0, "message": "Cancelled; nothing was deleted."}

  deleted = soft_delete_reports(owner_id, ids)
  logging.info("delete_reports deleted=%s ids=%s", deleted, ids)
  return {"ok": True, "deleted": deleted, "ids": ids}


tools = [run_sql, save_report, set_preference, delete_reports]
