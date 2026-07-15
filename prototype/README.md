# Chat Agent — Prototype

A working AI support agent powered by Claude. Searches historical cases, documentation, and analyzes error logs in real time.

## Setup

```bash
cd prototype
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY
```

## Run

Interactive mode:
```bash
python agent.py
```

Single query:
```bash
python agent.py "CPQ quote line totals are wrong after adding bundle product"
```

Log analysis:
```bash
python agent.py "Customer getting System.LimitException: Too many SOQL queries: 101 during CPQ quote save"
```

## How it works

1. You describe the issue (or paste an error log)
2. Claude decides which tools to call — case search, doc search, log analysis
3. Tools return matching results from the data sources
4. Claude synthesizes everything into a prioritized recommendation

## Files

| File | Purpose |
|---|---|
| `agent.py` | Main agent loop — sends messages to Claude, handles tool calls |
| `tools.py` | Tool definitions (schemas) + handlers (mock data, replace with live APIs) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Environment variable template |

## Extending with live data

Replace the mock functions in `tools.py`:

- `search_similar_cases()` → SOQL query against Org62 `Case` object
- `search_documentation()` → Salesforce Search API or internal KB API
- `analyze_error_log()` → Send to a log parsing service or enhance regex patterns
