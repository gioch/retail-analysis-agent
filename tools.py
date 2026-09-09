import logging

from langchain.tools import tool
from langchain_core.runnables import RunnableConfig

import sql
from preferences import OPTIONS, set_preference_value
from reports import save_report_row


@tool
def run_sql(intent: str, tables: list[str]) -> dict:
  """Run one analysis step against the database. Describe what the step should
  compute in plain English (intent) and name the tables it needs. Returns a result
  envelope with a result_id, the SQL used, row_count and rows (or a preview)."""
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


@tool
def save_report(title: str, body: str, result_ids: list[str], config: RunnableConfig) -> dict:
  """Save the analysis as a report in the user's library. Call this when the user asks for
  a report or asks to save the analysis. Pass a short title, the full report text in markdown,
  and the result_ids of the query results the report is based on."""
  report_id = save_report_row(config["configurable"]["user_id"], title, body, result_ids)
  return {"ok": True, "report_id": report_id, "title": title}


@tool
def set_preference(key: str, value: str, config: RunnableConfig) -> dict:
  """Remember how the user wants answers. Call this when the user states a lasting preference,
  e.g. "always show tables" or "keep it brief". key is 'format' (table, bullets, prose)
  or 'depth' (headline, standard, deep)."""
  if value not in OPTIONS.get(key, []):
    return {"ok": False, "error": f"'{key}' must be one of {OPTIONS.get(key)}"}
  set_preference_value(config["configurable"]["user_id"], key, value)
  return {"ok": True, key: value}


tools = [run_sql, save_report, set_preference]
