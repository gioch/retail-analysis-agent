import os

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "test")

from safety import mask_pii


def test_masks_emails_phones_addresses():
  text = "Top customer: john.doe@example.com, +1 (415) 555-0134, 221 Baker Street, spent $500."
  out = mask_pii(text)
  assert "john.doe" not in out and "555-0134" not in out and "Baker Street" not in out
  assert "$500" in out


@pytest.mark.parametrize("text", [
  "Revenue was $12,267.15 across 1,234 orders in 2025-03; basket size 98.14.",
  "Revenue increased by $2,261.00 (18.43%) this quarter compared to last quarter.",
  "Q2: $12,267.15, Q3: $15,096.06 (123 vs 151 customers, 2026-09-08).",
  "Outerwear & Coats grew by $1,807.81 (169.88%); order id 12345678901 shipped.",
])
def test_leaves_business_numbers_alone(text):
  assert mask_pii(text) == text


@pytest.mark.parametrize("phone", ["+1 (415) 555-0134", "415-555-0134", "415.555.0134", "(415) 555 0134"])
def test_masks_phone_shapes(phone):
  assert "[redacted]" in mask_pii(f"Call {phone} now")
