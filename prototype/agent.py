"""
Chat Agent — AI-powered real-time support assistant for Revenue Cloud engineers.
Uses Claude with tool use to search historical cases, documentation, and analyze logs.

Usage:
    python agent.py
    python agent.py "CPQ quote line totals are wrong after adding bundle"
"""

import os
import sys
import json
from pathlib import Path

# load .env if present
_env = Path(__file__).parent / ".env"
if _env.exists():
    for line in _env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import anthropic
from tools import TOOLS, handle_tool_call

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.spinner import Spinner
    from rich.live import Live
    RICH = True
    console = Console()
except ImportError:
    RICH = False

MODEL = "claude-sonnet-5"

SYSTEM = """You are Chat Agent, a real-time AI support assistant for Salesforce Revenue Cloud engineers.
You help engineers troubleshoot customer issues during live calls by instantly retrieving relevant
information and synthesizing actionable recommendations.

When given an issue description:
1. Search for similar historical cases to find proven resolutions
2. Search documentation for relevant KB articles or known issues
3. If logs are provided, analyze them for errors and patterns first, then search for matching cases
4. Synthesize all findings into a clear, prioritized troubleshooting recommendation

Response format:
- Lead with the most likely root cause (1-2 sentences)
- List step-by-step resolution steps
- Reference specific case numbers and doc titles you found
- Flag any escalation triggers (governor limits, data corruption, security issues)

Be concise — the engineer is on a live call. No filler, no disclaimers."""


def print_out(text, style=""):
    if RICH:
        console.print(text, style=style)
    else:
        print(text)


def print_panel(content, title="", border_style="blue"):
    if RICH:
        console.print(Panel(content, title=title, border_style=border_style))
    else:
        print(f"\n{'='*60}\n{title}\n{'='*60}\n{content}\n")


def run_agent(issue: str):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": issue}]

    print_panel(f"[bold]{issue}[/bold]", title="Issue", border_style="cyan")
    print_out("")

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    if RICH:
                        console.print(Panel(Markdown(block.text), title="[bold green]Recommendation[/bold green]", border_style="green"))
                    else:
                        print(f"\nRECOMMENDATION\n{'='*60}\n{block.text}\n")
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_display = {
                        "search_similar_cases": "Searching historical cases",
                        "search_documentation": "Searching documentation",
                        "analyze_error_log": "Analyzing error log",
                    }.get(block.name, block.name)

                    print_out(f"  [dim]→ {tool_display}...[/dim]")
                    result = handle_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            print_out("")
            messages.append({"role": "user", "content": tool_results})


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print_out("[bold red]Error:[/bold red] ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    if len(sys.argv) > 1:
        issue = " ".join(sys.argv[1:])
        run_agent(issue)
    else:
        if RICH:
            console.rule("[bold blue]Chat Agent — Revenue Cloud Support Assistant[/bold blue]")
            console.print("[dim]Describe the customer issue, or paste an error log. Type 'quit' to exit.[/dim]\n")
        else:
            print("\nChat Agent — Revenue Cloud Support Assistant")
            print("Describe the issue or paste an error log. Type 'quit' to exit.\n")

        while True:
            try:
                if RICH:
                    issue = console.input("[bold cyan]>[/bold cyan] ").strip()
                else:
                    issue = input("> ").strip()
            except (KeyboardInterrupt, EOFError):
                print_out("\n[dim]Goodbye.[/dim]")
                break

            if not issue:
                continue
            if issue.lower() in ("quit", "exit", "q"):
                break

            print_out("")
            run_agent(issue)
            print_out("")


if __name__ == "__main__":
    main()
