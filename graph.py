from typing import TypedDict, Annotated

from langchain.messages import AnyMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from openrouter.errors import TooManyRequestsResponseError

from llm import llm
from prompts import system_prompt

class MainState(TypedDict):
  messages: Annotated[list[AnyMessage], add_messages]
  token_budget: int
  tokens_used: int
  query_results: list
  error: str | None

def call_llm(state: MainState) -> dict:
  context = [SystemMessage(content=system_prompt())] + state["messages"]

  try:
    result = llm.invoke(context)
  except TooManyRequestsResponseError:
    return {
      "messages": [AIMessage(content="Provider is busy, try again shortly.")],
      "error": "rate_limited",
    }

  return {"messages": [result], "tokens_used": state["tokens_used"] + result.usage_metadata["total_tokens"]}

def build_graph():
  builder = StateGraph(MainState)
  builder.add_node("call_llm", call_llm)
  builder.add_edge(START, "call_llm")
  builder.add_edge("call_llm", END)
  return builder.compile(checkpointer=InMemorySaver())
