"""Create data/app.db with two demo users. Run once: python seed.py"""
import json
from datetime import datetime, timezone

from preferences import set_preference_value
from reports import db

set_preference_value("manager_a", "format", "table")
set_preference_value("manager_a", "depth", "standard")
set_preference_value("manager_b", "format", "bullets")
set_preference_value("manager_b", "depth", "headline")

DEMO_REPORTS = [
  ("manager_a", "Q1 2026 revenue review", "Revenue grew 8% in Q1 2026 driven by Outerwear. Action: extend the outerwear promotion into Q2."),
  ("manager_a", "Acme Corp account summary", "Acme Corp orders were flat quarter over quarter. Action: schedule a review with the account team."),
  ("manager_a", "California category mix 2025", "Jeans and Outerwear lead California revenue. Action: rebalance regional inventory."),
  ("manager_b", "Churn check August 2026", "Churn rate held at baseline. No action required."),
]

for owner, title, body in DEMO_REPORTS:
  exists = db.execute("SELECT 1 FROM reports WHERE owner_id = ? AND title = ?", (owner, title)).fetchone()
  if not exists:
    db.execute(
      "INSERT INTO reports (owner_id, title, body, result_ids, created_at) VALUES (?, ?, ?, ?, ?)",
      (owner, title, body, json.dumps([]), datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
db.commit()

print("Seeded preferences for manager_a (table, standard) and manager_b (bullets, headline), and 4 demo reports.")
