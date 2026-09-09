from reports import db

OPTIONS = {
  "format": ["table", "bullets", "prose"],
  "depth": ["headline", "standard", "deep"],
}
DEFAULTS = {"format": "prose", "depth": "standard"}

db.execute("""
  CREATE TABLE IF NOT EXISTS preferences (
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (user_id, key)
  )
""")


def get_preferences(user_id: str) -> dict:
  rows = db.execute("SELECT key, value FROM preferences WHERE user_id = ?", (user_id,)).fetchall()

  return {**DEFAULTS, **{row["key"]: row["value"] for row in rows}}


def set_preference_value(user_id: str, key: str, value: str) -> None:
  db.execute("INSERT OR REPLACE INTO preferences (user_id, key, value) VALUES (?, ?, ?)", (user_id, key, value))
  db.commit()
