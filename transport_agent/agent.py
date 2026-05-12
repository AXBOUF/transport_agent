"""
Transport NSW Agent — Claude Haiku with native tool use, SQL access, and chart rendering.
Returns {"answer": str, "chart": dict | None, "tools_used": list[str]}
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import anthropic
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from tools import run_tool, ANTHROPIC_TOOLS  # noqa: E402

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL  = "claude-haiku-4-5-20251001"
SYSTEM = (Path(__file__).parent / "skill.md").read_text()


# ── Agent loop ────────────────────────────────────────────────────────────────

def run(question: str) -> dict[str, Any]:
    messages    = [{"role": "user", "content": question}]
    chart_spec  = None
    tools_used  = []

    for _ in range(15):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=ANTHROPIC_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            answer = next(
                (b.text for b in response.content if hasattr(b, "text")),
                "No response."
            )
            return {"answer": answer, "chart": chart_spec, "tools_used": tools_used}

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type != "tool_use":
                    continue

                tools_used.append(block.name)
                print(f"  [tool: {block.name}]", flush=True)

                if block.name == "render_chart":
                    chart_spec = block.input
                    result = '{"status": "chart rendered in UI"}'
                else:
                    result = run_tool(block.name, block.input)

                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": block.id,
                    "content":     result,
                })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return {"answer": "Max steps reached.", "chart": chart_spec, "tools_used": tools_used}


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Transport NSW Agent (Claude Haiku) — Ctrl+C to quit\n")
    try:
        while True:
            q = input("You: ").strip()
            if not q or q.lower() in {"exit", "quit"}:
                break
            try:
                result = run(q)
                print(f"\nAgent: {result['answer']}")
                if result["chart"]:
                    c = result["chart"]
                    print(f"[Chart: {c.get('type')} — {c.get('title')}]")
                if result["tools_used"]:
                    print(f"[Tools: {', '.join(result['tools_used'])}]")
                print()
            except anthropic.APIError as e:
                print(f"API error: {e}\n", file=sys.stderr)
    except KeyboardInterrupt:
        pass
