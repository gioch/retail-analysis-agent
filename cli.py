from dotenv import load_dotenv

load_dotenv()

from rich.console import Console
from langchain.messages import HumanMessage

from graph import build_graph

console = Console()
TOKEN_BUDGET = 10000

def main():
  graph = build_graph()
  config = {"configurable": {"thread_id": "cli-session"}}

  while True:
    user_input = input("> ").strip()

    if not user_input:
      continue

    if user_input in ("/quit", "/exit", "exit()"):
      break

    with console.status("Thinking...", spinner="dots"):
      result = graph.invoke(
        {"messages": [HumanMessage(content=user_input)], "token_budget": TOKEN_BUDGET, "tokens_used": 0},
        config,
      )

    console.print(f"[bold cyan]agent[/] {result['messages'][-1].content}")


if __name__ == "__main__":
  main()
