import logging
from typing import TypedDict, Annotated

from langchain.messages import AnyMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import ToolNode, tools_condition

import llm
from prompts import system_prompt
import golden
from preferences import get_preferences
from safety import is_allowed, mask_pii, REFUSAL
from tools import tools

MAX_LLM_CALLS = 12
SALVAGE_NOTE = "The analysis budget for this question is used up. Give your final answer now from the results you already have. State plainly what could not be computed. Do not describe further queries or plans."


class MainState(TypedDict):
  messages: Annotated[list[AnyMessage], add_messages]
  refused: bool
  trios: str


def gate(state: MainState) -> dict:
  if is_allowed(state["messages"][-1].content):
    return {"refused": False}
  logging.warning("gate refused input=%r", state["messages"][-1].content[:200])
  return {"refused": True, "messages": [AIMessage(content=REFUSAL)]}


def after_gate(state: MainState) -> str:
  return END if state["refused"] else "retrieve"


def retrieve(state: MainState) -> dict:
  """Guaranteed before planning, not agent-optional: the model always sees relevant past analyses."""
  hits = golden.retrieve(state["messages"][-1].content)
  logging.info("retrieve trios=%s", [t["question"] for t in hits])
  return {"trios": golden.render(hits)}


def call_llm(state: MainState, config: RunnableConfig) -> dict:
  preferences = get_preferences(config["configurable"]["user_id"])
  context = [SystemMessage(content=system_prompt(preferences, state["trios"]))] + state["messages"]
  allowed_tools = tools

  if llm.usage["calls"] >= MAX_LLM_CALLS - 1:
    context.append(SystemMessage(content=SALVAGE_NOTE))
    allowed_tools = None

  result = llm.invoke(context, tools=allowed_tools)

  if not result.tool_calls:
    result.content = mask_pii(result.content)

  tool_names = [call["name"] for call in result.tool_calls]
  logging.info("call_llm tools=%s usage=%s", tool_names, llm.usage)
  return {"messages": [result]}

def build_graph():
  builder = StateGraph(MainState)
  builder.add_node("gate", gate)
  builder.add_node("retrieve", retrieve)
  builder.add_node("call_llm", call_llm)
  builder.add_node("tools", ToolNode(tools))
  builder.add_edge(START, "gate")
  builder.add_conditional_edges("gate", after_gate)
  builder.add_edge("retrieve", "call_llm")
  builder.add_conditional_edges("call_llm", tools_condition)
  builder.add_edge("tools", "call_llm")
  return builder.compile(checkpointer=InMemorySaver())
