from datetime import date

from bq_schema import schema as bq_schema


SYSTEM_PROMPT_TEMPLATE = """
# Role
Your name is Gilgamesh.
You are a capable and insightful analyst working for a retail company. Today is {today}.

# How you work
Answer analysis questions by breaking them into steps and calling run_sql once per step.
Each step computes one thing (a metric, a comparison, a breakdown). Simple questions need one step;
"why" questions need three or four: quantify the change, then decompose it, then localize the cause.
Read each result before deciding the next step. If a step returns ok: false, do not repeat it;
change the approach or continue without it and say so in the answer. When you have enough evidence,
answer in plain business language, cite the numbers, and end with action items if the user asked for a report.

# E-Commerce Database Schema
Here is the list of database tables and their descriptions:
{table_names}
"""


def system_prompt() -> str:
  table_names = "\n".join(f"{name} - {table.description}" for name, table in bq_schema.tables.items())
  return SYSTEM_PROMPT_TEMPLATE.format(table_names=table_names, today=date.today().isoformat())


SQL_GENERATION_PROMPT_TEMPLATE = """
You write one BigQuery Standard SQL SELECT query for the analysis step below.
Use only the tables and columns listed, follow the glossary definitions and the policy.
Return only the SQL, no explanation, no markdown.

# Glossary
{glossary}

# Policy
{policy}

# Tables
{tables}
"""


def sql_generation_prompt(tables: list[str]) -> str:
  return SQL_GENERATION_PROMPT_TEMPLATE.format(
    glossary="\n".join(f"- {k}: {v}" for k, v in bq_schema.glossary.items()),
    policy="\n".join(f"- {p}" for p in bq_schema.policy),
    tables=describe_tables(tables),
  )


def describe_tables(names: list[str]) -> str:
  """Detailed schema for the SQL generation prompt. Blocked columns are simply absent."""
  parts = []
  for name in names:
    table = bq_schema.tables.get(name)
    if table is None or not table.enabled:
      continue
    lines = [f"## {name}", table.description.strip(), "Joins: " + "; ".join(table.joins), "Columns:"]
    for col_name, col in table.columns.items():
      if col.allowed:
        values = f" one of {col.values}" if col.values else ""
        lines.append(f"- {col_name} ({col.type}){values}: {col.description or ''}".rstrip(": "))
    parts.append("\n".join(lines))
  return "\n\n".join(parts)
