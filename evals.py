"""Run every approved trio through the agent and let a judge model compare the answer
with the trio's own SQL executed directly. Usage: python evals.py"""
import json
import logging
import sys

from langchain.messages import HumanMessage, SystemMessage

import golden
import llm
import sql
import graph
from prompts import JUDGE_PROMPT



def reference_rows(trio: dict) -> list[dict]:
  rows = []
  for step in trio["analysis_plan"]:
    rows += sql.execute(step["purpose"], sql.validate(step["sql"]))["rows"]
  return rows


def judge(trio: dict, answer: str, reference: list[dict]) -> dict:
  content = f"Question: {trio['question']}\nExpected method: {trio['description']}\nReference rows: {json.dumps(reference)[:4000]}\nAnswer:\n{answer}"
  reply = llm.invoke([SystemMessage(content=JUDGE_PROMPT), HumanMessage(content=content)])
  return json.loads(reply.content.strip().removeprefix("```json").removesuffix("```"))


MAX_CALLS = graph.MAX_LLM_CALLS + sql.MAX_ATTEMPTS


def main() -> int:
  logging.basicConfig(filename="agent.log", level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", force=True)

  agent = graph.build_graph()
  failed = 0

  for trio in golden.trios:
    reference = reference_rows(trio)
    llm.reset_usage()
    config = {"configurable": {"thread_id": trio["question"], "user_id": "evals", "session_started_at": ""}}
    result = agent.invoke({"messages": [HumanMessage(content=trio["question"])], "trios": ""}, config)
    answer = result["messages"][-1].content
    verdict = judge(trio, answer, reference)

    problems = []
    if result["refused"]:
      problems.append("refused by gate")
    if "[redacted]" in answer:
      problems.append("PII redacted in answer")
    if llm.usage["calls"] > MAX_CALLS:
      problems.append(f"over budget: {llm.usage['calls']} calls")
    if not verdict["pass"]:
      problems.append(f"judge: {verdict['reason']}")

    failed += bool(problems)
    print(f"{'FAIL' if problems else 'PASS'}  {trio['question']}  ({llm.usage['calls']} calls, {llm.usage['tokens']} tokens)")
    print(f"      {'; '.join(problems) or verdict['reason']}")

  return failed


if __name__ == "__main__":
  sys.exit(main())
