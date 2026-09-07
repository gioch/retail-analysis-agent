from dotenv import load_dotenv
from rich.console import Console

from langgraph.graph.message import add_messages
from typing import TypedDict, Annotated

from langchain.messages import AnyMessage, SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openrouter import ChatOpenRouter
from openrouter.errors import TooManyRequestsResponseError

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from bq_schema import load_schema

load_dotenv()
console = Console()
bq_schema = load_schema()

# LLM configurations
# (I have to move this to the separate file)
llm_provider = ChatOpenRouter(model = "google/gemma-3-4b-it")

token_budget = 10000
system_prompt_template = PromptTemplate.from_template(
  """
    # Role
    Your name is Gilgamesh.
    You are capable and insightful analyst working for the retail company.

    # Overal ECommerce Database Schema
    You know data science and SQL helps you to generate insightful reports.
    Here is the list of database table names and their descriptions:
    {table_names}
  """
)

table_names = "\n".join(f"{name} - {table.description}" for name, table in bq_schema.tables.items())
system_prompt = system_prompt_template.format(table_names = table_names)

# State and Graph configurations
# (I have to move this to the separate file)
class MainState(TypedDict):
  messages: Annotated[list[AnyMessage], add_messages]
  token_budget: int
  tokens_used: int
  query_results: list

def call_llm(state: MainState) -> dict:
  context = [SystemMessage(content = system_prompt)] + state['messages']

  try:
    result = llm_provider.invoke(context)
  except TooManyRequestsResponseError:
    console.print(f"[bold cyan]agent[/] Currently the Provider is busy and asked us to wait :)")

  return { "messages": [result], "tokens_used": state['tokens_used'] + result.usage_metadata["total_tokens"] }

def main():
  graph_builder = StateGraph(MainState)
  graph_builder.add_node('call_llm', call_llm)
  graph_builder.add_edge(START, "call_llm")
  graph_builder.add_edge("call_llm", END)
  graph = graph_builder.compile(checkpointer=InMemorySaver())

  while True:
    user_input = input("> ").strip()

    if not user_input:
      continue

    if user_input in ("/quit", "/exit", "exit()"):
      break

    with console.status("Thinking...", spinner="dots"):
      result = graph.invoke(
        { "messages": [HumanMessage(content = user_input)], "token_budget": token_budget, "tokens_used": 0 },
        { "configurable": { "thread_id": "cli-session" } }
      )

    console.print(f"[bold cyan]agent[/] {result['messages'][-1].content}")

if __name__ == "__main__":
  main()