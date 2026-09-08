from dotenv import load_dotenv

load_dotenv()

import argparse

from rich.console import Console
from rich.markdown import Markdown
from langchain.messages import HumanMessage

from graph import build_graph

console = Console()
TOKEN_BUDGET = 10000

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
    console.print("No analysis steps yet.")
  else:
    console.print(f"Unknown command: {user_input}. Type /help.")


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

    with console.status("Thinking...", spinner="dots"):
      result = graph.invoke(
        {"messages": [HumanMessage(content=user_input)], "token_budget": TOKEN_BUDGET, "tokens_used": 0},
        config,
      )

    console.print("[bold cyan]agent[/]")
    console.print(Markdown(result["messages"][-1].content))


if __name__ == "__main__":
  main()
