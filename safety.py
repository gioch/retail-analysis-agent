import re

from langchain.messages import SystemMessage, HumanMessage

import llm
from prompts import GATE_PROMPT

REFUSAL = "I can only help with analysis of the company's sales, product and customer data, and I can't share personal customer information."

PII_PATTERNS = [
  re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
  re.compile(r"\+?\d[\d\s().-]{8,}\d"),
  re.compile(r"\b\d{1,5}\s+\w+(\s\w+)?\s(Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Boulevard|Blvd)\b", re.IGNORECASE),
]


def is_allowed(user_input: str) -> bool:
  """One cheap classification call; anything but an explicit ALLOW is refused."""
  reply = llm.invoke(llm.chat, [SystemMessage(content=GATE_PROMPT), HumanMessage(content=user_input)])
  return reply.content.strip().upper().startswith("ALLOW")


def mask_pii(text: str) -> str:
  for pattern in PII_PATTERNS:
    text = pattern.sub("[redacted]", text)
  return text
