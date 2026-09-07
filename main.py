import os
from dotenv import load_dotenv
from langchain_openrouter import ChatOpenRouter
from langchain.messages import SystemMessage, AIMessage, HumanMessage

load_dotenv()

class Agent:
  def __init__(self, model: str = "google/gemma-3-4b-it") -> None:
    self.model = model
    self.llm_provider = ChatOpenRouter(model = model)
    self.messages = []

  def invoke(self, user_prompt: str) -> str:
    self.messages.append(HumanMessage(content=user_prompt))
    response = self.llm_provider.invoke(self.messages)
    self.messages.append(response)

    return response.content

  def conversation(self) -> list:
    return [m.content for m in self.messages]


def main():
  agent = Agent()

  while True:
    user_input = input("> ").strip()

    if not user_input:
      continue

    if user_input in ("/quit", "/exit", "exit()"):
      break

    if user_input in ("/history"):
      print(agent.conversation())
      continue

    response = agent.invoke(user_input)

    print(response)

if __name__ == "__main__":
  main()