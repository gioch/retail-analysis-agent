import os

os.environ.setdefault("OPENROUTER_API_KEY", "test")

from safety import mask_pii


def test_masks_emails_phones_addresses():
  text = "Top customer: john.doe@example.com, +1 (415) 555-0134, 221 Baker Street, spent $500."
  out = mask_pii(text)
  assert "john.doe" not in out and "555-0134" not in out and "Baker Street" not in out
  assert "$500" in out


def test_leaves_business_numbers_alone():
  text = "Revenue was $12,267.15 across 1,234 orders in 2025-03; basket size 98.14."
  assert mask_pii(text) == text
