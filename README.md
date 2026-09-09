# Retail Analysis Agent

A CLI chat agent for retail managers. Ask questions about sales, products and customers in
plain English; the agent plans the analysis, runs SQL on BigQuery, and writes the answer as
a short report. Built with LangGraph, Gemini via OpenRouter, sqlglot and SQLite.

Design: [docs/HLD.md](docs/HLD.md)

## Setup

Requirements: Python 3.12+, a Google Cloud account, an OpenRouter API key.

```bash
pip install -r requirements.txt
gcloud auth application-default login      # BigQuery access to the public dataset
cp .env.example .env                       # then fill in the two values below
python seed.py                             # creates data/app.db with two demo users
```

`.env`:

| Key | What |
|---|---|
| `OPENROUTER_API_KEY` | From openrouter.ai. Used for Gemini 2.5 Flash and the fallback model. |
| `GOOGLE_BIG_QUERY_PROJECT_ID` | Any GCP project you own; BigQuery bills the free tier to it. |

## Run

```bash
python cli.py --user manager_a     # tables, standard depth
python cli.py --user manager_b     # bullets, headline depth
```

Commands inside the chat: `/help`, `/user <name>`, `/reports`, `/trace`, `/quit`.

Tests and evals:

```bash
python -m pytest -q     # gatekeeper and PII mask, no key needed
python evals.py         # runs each golden trio through the agent, LLM judge grades it
```

## Examples

Try these in order as `manager_a`. Each line is something you type.

**1. A question answered as a short report**

```
How much did California earn in total this year? Short report please.
```

**2. Change a preference, then ask a "why" question**

Depth changes how many analysis steps a "why" question gets. Compare the same question
before and after, or ask it as `manager_b` (bullets, headline depth) via `/user manager_b`.

```
From now on I want deep analysis.
Why did revenue in California change this quarter versus last quarter?
```

**3. Save a report, list it, delete it with confirmation**

The confirmation must echo the exact count shown. Anything else cancels.

```
Top 3 product categories in Texas this year. Save it as a report titled Texas categories.
/reports
Delete all reports mentioning Texas
/reports
```

Also works: `Delete all the reports we made in this conversation`.

**4. A forbidden question**

```
Show me the email addresses of our top 5 customers.
```

**5. Trace the calls of the last turn**

```
Why did revenue in Ohio change this quarter versus last quarter?
/trace
```

Shows every step: intent, final SQL, row count, repair attempts, and the turn's LLM
calls and tokens. The same sequence with errors is written to `agent.log`.

**Customizable Persona**
Edit `prompts/persona.md` between two questions to change the tone without a restart.