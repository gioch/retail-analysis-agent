import os
import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "test")

from sql import validate, SqlRejected


@pytest.mark.parametrize("sql", [
  "DELETE FROM orders",
  "UPDATE users SET age = 1",
  "DROP TABLE orders",
  "SELECT id FROM users; DELETE FROM orders",
  "SELECT * FROM orders",
  "SELECT email FROM users",
  "SELECT u.first_name FROM users u",
  "SELECT id FROM secret_table",
  "SELECT id FROM events",
  "SELECT nonexistent FROM orders",
  "SELECT id FROM users WHERE",
  "SELECT id FROM users WHERE email LIKE '%@%'",
  "SELECT id FROM users UNION ALL SELECT email FROM users",
  "SELECT id FROM users; -- ignore previous rules",
  "SELECT id FROM (SELECT email AS id FROM users)",
  "SELECT LOWER(email) AS e FROM users",
])
def test_rejects(sql):
  with pytest.raises(SqlRejected):
    validate(sql)


def test_qualifies_tables_and_injects_limit():
  out = validate("SELECT order_id FROM orders")
  assert "`bigquery-public-data`.thelook_ecommerce.orders" in out
  assert out.endswith("LIMIT 1000")


def test_keeps_smaller_limit_and_caps_larger():
  assert validate("SELECT order_id FROM orders LIMIT 10").endswith("LIMIT 10")
  assert validate("SELECT order_id FROM orders LIMIT 99999").endswith("LIMIT 1000")


def test_allows_joins_ctes_and_aliases():
  sql = """
    WITH ca AS (SELECT id FROM users WHERE state = 'California')
    SELECT p.category, SUM(oi.sale_price) AS revenue
    FROM order_items oi
    JOIN ca ON ca.id = oi.user_id
    JOIN products p ON p.id = oi.product_id
    GROUP BY category ORDER BY revenue DESC
  """
  assert "revenue" in validate(sql)
