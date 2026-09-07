import os
import yaml
from pydantic import BaseModel
from typing import Literal
from bq_client import BigQueryRunner

bg_client = BigQueryRunner(project_id=os.getenv("GOOGLE_BIG_QUERY_PROJECT_ID"))

class ECommerceDBColumn(BaseModel):
  type: Literal["INTEGER", "STRING", "TIMESTAMP", "FLOAT", "BOOLEAN"]
  pii: bool = None
  allowed: bool
  description: str = None

class ECommerceDBTable(BaseModel):
  enabled: bool
  description: str = None
  joins: list[str] = []
  columns: dict[str, ECommerceDBColumn]
  values: list[str] | None = None

class ECommerceDBSchema(BaseModel):
  dataset: str
  tables: dict[str, ECommerceDBTable]

def load_schema() -> ECommerceDBSchema:
  with open("ecomerce_db_schema.yml") as f:
    raw_ecomerce_db_schema = yaml.safe_load(f)

  ecomerce_db_schema = ECommerceDBSchema.model_validate(raw_ecomerce_db_schema)

  # Temporarily disabled
  # for table in ecomerce_db_schema.tables:
    # source_table = bg_client.get_table_schema(table)
    # console.print(source_table)

  print(f"[bold red]--------------------------------------")
  print(f"[bold red]TO BE IMPLEMENTED! Actual table and column name checker")
  print(f"[bold red]--------------------------------------")

  return ecomerce_db_schema