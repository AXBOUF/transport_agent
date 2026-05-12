from __future__ import annotations

import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows so arrow/emoji characters don't crash cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import anthropic
from dotenv import load_dotenv

from tools import run_tool, ANTHROPIC_TOOLS

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM = (Path(__file__).parent / "skill.md").read_text()


# ── Agent loop ────────────────────────────────────────────────────────────────

def run(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    for _ in range(10):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM,
            tools=ANTHROPIC_TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
            return "No response."

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [tool: {block.name}]", flush=True)
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "Max steps reached."


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Transport Agent (Claude Haiku) — Ctrl+C to quit\n")
    try:
        while True:
            q = input("You: ").strip()
            if not q or q.lower() in {"exit", "quit"}:
                break
            try:
                print(f"\nAgent: {run(q)}\n")
            except anthropic.APIError as e:
                print(f"API error: {e}\n", file=sys.stderr)
    except KeyboardInterrupt:
        pass
