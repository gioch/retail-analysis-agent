import sqlglot
from sqlglot import exp

from bq_schema import schema

MAX_ROWS = 1000


class SqlRejected(Exception):
  pass


def validate(sql: str) -> str:
  """Validates SQL, return it qualified and row-limited."""
  try:
    statements = sqlglot.parse(sql, read="bigquery")
  except sqlglot.errors.ParseError as e:
    raise SqlRejected(f"Syntax error: {e}")

  if len(statements) != 1:
    raise SqlRejected("Only one statement is allowed.")

  query = statements[0]
  if not isinstance(query, exp.Select):
    raise SqlRejected(f"Only SELECT is allowed, got {query.key.upper()}.")

  if list(query.find_all(exp.Star)):
    raise SqlRejected("SELECT * is not allowed; list the columns explicitly.")

  _check_tables(query)
  _check_columns(query)

  return _rewrite(query).sql(dialect="bigquery")


def _check_tables(query: exp.Select) -> None:
  cte_names = {cte.alias for cte in query.find_all(exp.CTE)}
  enabled = {name for name, t in schema.tables.items() if t.enabled}

  for table in query.find_all(exp.Table):
    if table.name not in enabled and table.name not in cte_names:
      raise SqlRejected(f"Unknown table '{table.name}'. Available tables: {', '.join(sorted(enabled))}.")


def _check_columns(query: exp.Select) -> None:
  allowed, blocked = set(), set()
  for table in schema.tables.values():
    if table.enabled:
      for name, col in table.columns.items():
        (allowed if col.allowed else blocked).add(name)

  aliases = {a.alias for a in query.find_all(exp.Alias)} | {cte.alias for cte in query.find_all(exp.CTE)}

  for column in query.find_all(exp.Column):
    if column.name in blocked:
      raise SqlRejected(f"Column '{column.name}' is not available; remove it from the query.")
    if column.name not in allowed and column.name not in aliases:
      raise SqlRejected(f"Unknown column '{column.name}'. Check the table description for available columns.")


def _rewrite(query: exp.Select) -> exp.Select:
  catalog, db = schema.dataset.split(".")
  for table in query.find_all(exp.Table):
    if table.name in schema.tables and not table.db:
      table.set("catalog", exp.to_identifier(catalog))
      table.set("db", exp.to_identifier(db))

  limit = query.args.get("limit")
  if limit is None or int(limit.expression.this) > MAX_ROWS:
    query = query.limit(MAX_ROWS)

  return query
