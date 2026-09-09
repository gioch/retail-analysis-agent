import logging
from pathlib import Path

import yaml

BUCKET_DIR = Path(__file__).parent / "golden_bucket"
TOP_K = 2


def load_trios() -> list[dict]:
  trios = []
  for path in sorted(BUCKET_DIR.glob("*.yml")):
    trio = yaml.safe_load(path.read_text())
    if trio.get("status") == "approved":
      trios.append(trio)
  logging.info("golden bucket loaded trios=%s", len(trios))
  return trios


trios = load_trios()


def retrieve(question: str) -> list[dict]:
  """A trio matches when its tags appear in the question; production swaps this for embeddings."""
  words = question.lower()
  scored = [(sum(tag in words for tag in trio["tags"]), trio) for trio in trios]
  hits = [trio for score, trio in sorted(scored, key=lambda pair: pair[0], reverse=True)[:TOP_K] if score > 0]
  if not hits:
    logging.info("golden bucket coverage miss question=%r", question[:120])
  return hits


def render(hits: list[dict]) -> str:
  if not hits:
    return ""
  parts = ["# Past analyses by our analysts. Adapt the method to the current question: substitute the user's region, period and metric into every step intent; never copy a step verbatim."]
  for trio in hits:
    parts.append(f"## {trio['question']}\n{trio['description'].strip()}\nSteps:")
    for i, step in enumerate(trio["analysis_plan"], 1):
      parts.append(f"{i}. {step['purpose']}\n```sql\n{step['sql'].strip()}\n```")
  return "\n".join(parts)
