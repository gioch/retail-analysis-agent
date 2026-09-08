from typing import TypedDict, Annotated

from langchain.messages import AnyMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from openrouter.errors import TooManyRequestsResponseError

import llm
from prompts import system_prompt
from reports import save_report
from safety import is_allowed, mask_pii, REFUSAL
from sql import run_sql

tools = [run_sql, save_report]
llm_with_tools = llm.chat.bind_tools(tools)

MAX_LLM_CALLS = 12
SALVAGE_NOTE = "The analysis budget for this question is used up. Give your final answer now from the results you already have. State plainly what could not be computed. Do not describe further queries or plans."


class MainState(TypedDict):
  messages: Annotated[list[AnyMessage], add_messages]
  refused: bool
  error: str | None


def gate(state: MainState) -> dict:
  if is_allowed(state["messages"][-1].content):
    return {"refused": False}
  return {"refused": True, "messages": [AIMessage(content=REFUSAL)]}


def after_gate(state: MainState) -> str:
  return END if state["refused"] else "call_llm"


def call_llm(state: MainState) -> dict:
  context = [SystemMessage(content=system_prompt())] + state["messages"]
  model = llm_with_tools

  if llm.usage["calls"] >= MAX_LLM_CALLS - 1:
    context.append(SystemMessage(content=SALVAGE_NOTE))
    model = llm.chat

  try:
    result = llm.invoke(model, context)
  except TooManyRequestsResponseError:
    return {
      "messages": [AIMessage(content="Provider is busy, try again shortly.")],
      "error": "rate_limited",
    }

  if not result.tool_calls:
    result.content = mask_pii(result.content)

  return {"messages": [result]}

def build_graph():
  builder = StateGraph(MainState)
  builder.add_node("gate", gate)
  builder.add_node("call_llm", call_llm)
  builder.add_node("tools", ToolNode(tools))
  builder.add_edge(START, "gate")
  builder.add_conditional_edges("gate", after_gate)
  builder.add_conditional_edges("call_llm", tools_condition)
  builder.add_edge("tools", "call_llm")
  return builder.compile(checkpointer=InMemorySaver())
