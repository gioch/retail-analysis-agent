import os
from dotenv import load_dotenv
from rich.console import Console

from langchain_openrouter import ChatOpenRouter
from langchain.messages import SystemMessage, AIMessage, HumanMessage

class Agent:
  def __init__(self, model: str = "google/gemma-3-4b-it") -> None:
    self.model = model
    self.llm_provider = ChatOpenRouter(model = model)
    self.messages = []

  def invoke(self, user_prompt: str) -> str:
    self.messages.append(HumanMessage(content=user_prompt))
    response = self.llm_provider.invoke(self.messages)
    self.messages.append(response)

    return response

  def conversation(self) -> list:
    return [m.content for m in self.messages]


def main():
  load_dotenv()

  agent = Agent()
  console = Console()

  while True:
    user_input = input("> ").strip()

    if not user_input:
      continue

    if user_input in ("/quit", "/exit", "exit()"):
      break

    if user_input in ("/history"):
      console.print(f"[bold cyan]agent[/] {agent.conversation()}")
      continue

    with console.status("Thinking...", spinner="dots"):
      response = agent.invoke(user_input)
      reply = response.content

      console.print(f"[bold cyan]agent[/] {reply}")

if __name__ == "__main__":
  main()