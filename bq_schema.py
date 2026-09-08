import os
import yaml
from pydantic import BaseModel, ConfigDict
from typing import Literal
from bq_client import BigQueryRunner

# bq_client = BigQueryRunner(project_id=os.getenv("GOOGLE_BIG_QUERY_PROJECT_ID"))


class StrictModel(BaseModel):
  model_config = ConfigDict(extra="forbid")


class ECommerceDBColumn(StrictModel):
  type: Literal["INTEGER", "STRING", "TIMESTAMP", "FLOAT", "BOOLEAN"]
  allowed: bool
  pii: bool = False
  description: str | None = None
  values: list[str] | None = None


class ECommerceDBTable(StrictModel):
  enabled: bool
  description: str | None = None
  joins: list[str] = []
  columns: dict[str, ECommerceDBColumn]


class ECommerceDBSchema(StrictModel):
  dataset: str
  tables: dict[str, ECommerceDBTable]
  glossary: dict[str, str] = {}
  policy: list[str] = []


def load_schema() -> ECommerceDBSchema:
  with open("ecomerce_db_schema.yml") as f:
    raw = yaml.safe_load(f)

  schema = ECommerceDBSchema.model_validate(raw)

  # TODO: verify table and column names against BigQuery (bq_client.get_table_schema)
  return schema
