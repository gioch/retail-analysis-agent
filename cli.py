from dotenv import load_dotenv

load_dotenv()

import argparse

from rich.console import Console
from rich.markdown import Markdown
from langchain.messages import HumanMessage

import llm
from graph import build_graph
from sql import results

console = Console()

HELP = """
/help          show this message
/user <name>   switch the current user
/trace         show the analysis steps of this session
/quit          exit
"""


def handle_command(user_input: str, session: dict) -> None:
  command, _, arg = user_input.partition(" ")

  if command == "/help":
    console.print(HELP)
  elif command == "/user" and arg:
    session["user"] = arg
    console.print(f"Switched to user [bold]{arg}[/]")
  elif command == "/trace":
    print_trace()
  else:
    console.print(f"Unknown command: {user_input}. Type /help.")


def print_trace() -> None:
  if not results:
    console.print("No analysis steps yet.")
  for result in results.values():
    console.print(f"[bold]{result['result_id']}[/] {result['intent']}")
    console.print(f"  rows: {result['row_count']}  attempts: {result.get('attempts', 1)}")
    console.print(f"  [dim]{result['sql']}[/]")
  console.print(f"Last turn: {llm.usage['calls']} LLM calls, {llm.usage['tokens']} tokens")


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--user", default="manager_a")
  args = parser.parse_args()

  graph = build_graph()
  session = {"user": args.user}
  config = {"configurable": {"thread_id": "cli-session"}}

  console.print(f"Logged in as [bold]{session['user']}[/]. Type /help for commands.")

  while True:
    try:
      user_input = input("> ").strip()
    except (KeyboardInterrupt, EOFError):
      break

    if not user_input:
      continue

    if user_input in ("/quit", "/exit"):
      break

    if user_input.startswith("/"):
      handle_command(user_input, session)
      continue

    llm.reset_usage()
    with console.status("Thinking...", spinner="dots"):
      result = graph.invoke({"messages": [HumanMessage(content=user_input)]}, config)

    console.print("[bold cyan]agent[/]")
    console.print(Markdown(result["messages"][-1].content))


if __name__ == "__main__":
  main()
