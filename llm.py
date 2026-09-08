from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter

load_dotenv()

chat = ChatOpenRouter(model="google/gemini-2.5-flash")

usage = {"calls": 0, "tokens": 0}


def invoke(model, messages):
  """Every LLM call goes through here so the per-turn budget sees all of them."""
  result = model.invoke(messages)
  usage["calls"] += 1
  usage["tokens"] += (result.usage_metadata or {}).get("total_tokens", 0)
  return result


def reset_usage() -> None:
  usage["calls"] = 0
  usage["tokens"] = 0
