from dotenv import load_dotenv

load_dotenv()

import argparse
import logging
from datetime import datetime, timezone

from rich.console import Console
from rich.markdown import Markdown
from langchain.messages import HumanMessage
from langgraph.types import Command

import llm
from graph import build_graph
from preferences import get_preferences
from reports import list_reports
from sql import results

console = Console()
logging.basicConfig(filename="agent.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)  # bq_client configures logging first
logging.getLogger("httpx").setLevel(logging.WARNING)

HELP = """
/help          show this message
/user <name>   switch the current user
/trace         show the analysis steps of this session
/reports       list your saved reports
/quit          exit
"""


def handle_command(user_input: str, session: dict) -> None:
  command, _, arg = user_input.partition(" ")

  if command == "/help":
    console.print(HELP)
  elif command == "/user" and arg:
    session["user"] = arg
    console.print(f"Switched to user [bold]{arg}[/] {get_preferences(arg)}")
  elif command == "/trace":
    print_trace()
  elif command == "/reports":
    rows = list_reports(session["user"])
    for row in rows:
      console.print(f"[bold]#{row['id']}[/] {row['title']}  [dim]{row['created_at']}[/]")
    if not rows:
      console.print("No saved reports.")
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


def ask(graph, user_input: str, config: dict) -> str:
  """Stream node updates so the spinner narrates each analysis step; return the final reply."""
  step = 0
  graph_input = {"messages": [HumanMessage(content=user_input)], "trios": ""}
  while True:
    with console.status("Thinking...", spinner="dots") as status:
      for update in graph.stream(graph_input, config, stream_mode="updates"):
        if "__interrupt__" in update:
          status.stop()
          graph_input = Command(resume=confirm(update["__interrupt__"][0].value))
          break
        node = "gate" if "gate" in update else "call_llm"
        message = update.get(node, {}).get("messages", [None])[-1]
        if message is not None and message.tool_calls:
          step += 1
          call = message.tool_calls[0]
          status.update(f"Step {step}: {call['args'].get('intent', call['name'])[:90]}")
        elif message is not None:
          return message.content
      else:
        return "No answer was produced."


def confirm(request: dict) -> str:
  console.print("[bold]These reports will be deleted:[/]")
  for report in request["reports"]:
    console.print(f"  #{report['id']} {report['title']}  [dim]{report['created_at']}[/]")
  console.print(f"Type [bold]{request['expected']}[/] to confirm, anything else to cancel.")
  try:
    return input("> ").strip()
  except (KeyboardInterrupt, EOFError):
    return ""


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--user", default="manager_a")
  args = parser.parse_args()

  graph = build_graph()
  session = {"user": args.user, "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}

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
    config = {"configurable": {"thread_id": "cli-session", "user_id": session["user"], "session_started_at": session["started_at"]}}
    try:
      answer = ask(graph, user_input, config)
    except Exception:
      logging.exception("Turn failed")
      answer = "Something went wrong on my side and I could not finish this request. Please try again, or ask in a different way."

    console.print("[bold cyan]agent[/]")
    console.print(Markdown(answer))


if __name__ == "__main__":
  main()
