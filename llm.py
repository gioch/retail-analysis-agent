import logging
import time

from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from openrouter import errors
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

load_dotenv()

PRIMARY = ChatOpenRouter(model="google/gemini-2.5-flash", timeout=60_000, max_retries=0)  # timeout is in ms; tenacity owns retries
FALLBACK = ChatOpenRouter(model="openai/gpt-4o-mini", timeout=60_000, max_retries=0)

TRANSIENT = (
  errors.TooManyRequestsResponseError,
  errors.ProviderOverloadedResponseError,
  errors.ServiceUnavailableResponseError,
  errors.InternalServerResponseError,
  errors.BadGatewayResponseError,
  errors.RequestTimeoutResponseError,
  errors.EdgeNetworkTimeoutResponseError,
  errors.NoResponseError,
)
FATAL = (errors.UnauthorizedResponseError, errors.PaymentRequiredResponseError, errors.ForbiddenResponseError)

BREAKER_THRESHOLD = 3
BREAKER_COOLDOWN = 60

usage = {"calls": 0, "tokens": 0}
breaker = {"failures": 0, "open_until": 0.0}


def invoke(messages, tools=None):
  """Every LLM call goes through here: budget accounting, retries, and primary → fallback switching."""
  if time.time() < breaker["open_until"]:
    return _call(FALLBACK, messages, tools)

  try:
    result = _call(PRIMARY, messages, tools)
  except FATAL:
    raise
  except Exception as e:
    _trip_breaker()
    logging.warning("Primary provider failed (%s), using fallback", type(e).__name__)
    return _call(FALLBACK, messages, tools)

  breaker["failures"] = 0
  return result


def _call(model, messages, tools):
  if tools:
    model = model.bind_tools(tools)
  result = _invoke_with_retry(model, messages)
  usage["calls"] += 1
  usage["tokens"] += (result.usage_metadata or {}).get("total_tokens", 0)
  return result


@retry(retry=retry_if_exception_type(TRANSIENT), stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
def _invoke_with_retry(model, messages):
  return model.invoke(messages)


def _trip_breaker() -> None:
  breaker["failures"] += 1
  if breaker["failures"] >= BREAKER_THRESHOLD:
    breaker["open_until"] = time.time() + BREAKER_COOLDOWN
    logging.warning("Circuit breaker open for %ss", BREAKER_COOLDOWN)


def reset_usage() -> None:
  usage["calls"] = 0
  usage["tokens"] = 0
