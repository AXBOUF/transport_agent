from __future__ import annotations

import sys

import anthropic

from config import make_client, make_engine
from tools import TOOL_SCHEMAS, dispatch

MODEL = "claude-opus-4-7"

SYSTEM = """You are a transport data analyst with direct access to a PostgreSQL database
containing Transport for NSW GTFS (General Transit Feed Specification) data.

The database has a `raw` schema with 11 tables (all columns stored as TEXT):
- agency         — transit agencies operating routes
- routes         — bus/train/ferry routes per agency
- trips          — individual scheduled trips on routes
- stop_times     — every stop on every trip with arrival/departure times
- stops          — physical stop locations with lat/lon coordinates
- calendar       — weekly service patterns (Mon–Sun flags + date range)
- calendar_dates — exceptions to the calendar (extra or removed service days)
- shapes         — geographic polylines defining route paths (sequence of lat/lon points)
- levels         — accessibility levels for multi-level stations
- pathways       — walking connections between platforms within a station
- notes          — supplementary notes attached to trips or stop_times

Use the available tools to explore tables and answer questions accurately.
Always run queries to verify facts — do not guess from memory.
When displaying results, format them as readable summaries or tables.
Only SELECT queries are permitted — the database is read-only."""


def _run_tool_loop(
    client: anthropic.Anthropic,
    engine,
    messages: list,
) -> str:
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            thinking={"type": "adaptive"},
            system=SYSTEM,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            texts = [b.text for b in response.content if b.type == "text"]
            return "\n".join(texts)

        # stop_reason == "tool_use" — execute tools and loop
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  [tool: {block.name}]", flush=True)
                result = dispatch(engine, block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "user", "content": tool_results})


def main() -> None:
    client = make_client()
    engine = make_engine()
    messages: list = []

    print("Transport DB Agent — ask anything about the GTFS data (Ctrl+C or 'exit' to quit)\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except EOFError:
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit", "q"}:
                break

            messages.append({"role": "user", "content": user_input})

            try:
                reply = _run_tool_loop(client, engine, messages)
            except anthropic.APIError as exc:
                print(f"API error: {exc}\n", file=sys.stderr)
                messages.pop()
                continue

            messages.append({"role": "assistant", "content": reply})
            print(f"\nAgent: {reply}\n")

    except KeyboardInterrupt:
        pass

    print("Bye!")


if __name__ == "__main__":
    main()
