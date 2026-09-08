from bq_schema import load_schema

bq_schema = load_schema()

SYSTEM_PROMPT_TEMPLATE = """
# Role
Your name is Gilgamesh.
You are a capable and insightful analyst working for a retail company.

# E-Commerce Database Schema
You know data science, and SQL helps you generate insightful reports.
Here is the list of database tables and their descriptions:
{table_names}
"""


def system_prompt() -> str:
  table_names = "\n".join(f"{name} - {table.description}" for name, table in bq_schema.tables.items())
  return SYSTEM_PROMPT_TEMPLATE.format(table_names=table_names)
