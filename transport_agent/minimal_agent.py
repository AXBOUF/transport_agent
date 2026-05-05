from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests

from tools import run_tool, tools_prompt

# ── LLM ──────────────────────────────────────────────────────────────────────

LLM_URL = "https://www.munalbaraili.com/llm"
LLM_HEADERS = {"x-api-key": "mysecretkey"}
MODEL = "qwen2.5:7b"


def call_llm(prompt: str) -> str:
    r = requests.post(LLM_URL, headers=LLM_HEADERS, timeout=60,
                      json={"model": MODEL, "prompt": prompt, "stream": False})
    r.raise_for_status()
    return r.json()["response"]


# ── Skill ─────────────────────────────────────────────────────────────────────

_skill = (Path(__file__).parent / "skill.md").read_text()
SYSTEM = f"{_skill}\n\n## Available tools\n{tools_prompt()}"


# ── Agent loop ────────────────────────────────────────────────────────────────

def run(question: str) -> str:
    turns = [f"User: {question}"]

    for _ in range(10):
        prompt = SYSTEM + "\n\n" + "\n".join(turns) + "\nAssistant:"
        raw = call_llm(prompt)

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = None
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                pass

        if parsed is None:
            return raw.strip()
        if "answer" in parsed:
            return str(parsed["answer"])
        if "tool" in parsed:
            name = parsed["tool"]
            print(f"  [tool: {name}]", flush=True)
            result = run_tool(name, parsed.get("input", {}))
            turns.append(f"Assistant: {raw.strip()}")
            turns.append(f"Tool result: {result}")

    return "Max steps reached."


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Minimal agent — Ctrl+C to quit\n")
    try:
        while True:
            q = input("You: ").strip()
            if not q or q.lower() in {"exit", "quit"}:
                break
            try:
                print(f"\nAgent: {run(q)}\n")
            except requests.RequestException as e:
                print(f"LLM error: {e}\n", file=sys.stderr)
    except KeyboardInterrupt:
        pass
