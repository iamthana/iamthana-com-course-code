"""Review a stdio MCP server's tools before approving it, then pin them so a later change is caught.

  uv run python review_tools.py review SERVER.py   print every tool in full and flag suspicious markers
  uv run python review_tools.py pin SERVER.py      save a hash of each tool to tools.lock.json
  uv run python review_tools.py check SERVER.py    compare the server's tools with the pinned hashes
"""

import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters

LOCK_FILE = Path(__file__).parent / "tools.lock.json"
MAX_DESCRIPTION_LENGTH = 500

SUSPICIOUS_PATTERNS = {
    "hidden-instruction tag": r"<\s*(important|system|instructions?)\s*>",
    "asks to keep a step from the user": r"do not (mention|tell)|don't (mention|tell)|without telling",
    "points at another server's data": r"\w+://\S+|from the \w+ server",
    "reads local files": r"~/|/etc/|\bread the file",
    "overrides earlier instructions": r"ignore (all |any )?(previous|prior|above)",
}


async def fetch_tools(script: str) -> dict:
    async with Client(StdioServerParameters(command=sys.executable, args=[script])) as client:
        return {tool.name: tool for tool in (await client.list_tools()).tools}


def fingerprint(tool) -> str:
    content = {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def find_flags(tool) -> list[str]:
    description = tool.description or ""
    flags = [label for label, pattern in SUSPICIOUS_PATTERNS.items() if re.search(pattern, description, re.IGNORECASE)]
    if len(description) > MAX_DESCRIPTION_LENGTH:
        flags.append(f"description longer than {MAX_DESCRIPTION_LENGTH} characters")
    return flags


def show(tool) -> list[str]:
    flags = find_flags(tool)
    print(f"--- {tool.name}  sha256 {fingerprint(tool)[:12]}")
    print(tool.description or "(no description)")
    print("input schema:", json.dumps(tool.input_schema, sort_keys=True))
    for flag in flags:
        print("FLAG:", flag)
    print()
    return flags


async def review(script: str) -> int:
    tools = await fetch_tools(script)
    flagged = sum(1 for tool in tools.values() if show(tool))
    print(f"{len(tools)} tools, {flagged} flagged")
    return 1 if flagged else 0


async def pin(script: str) -> int:
    tools = await fetch_tools(script)
    lock = json.loads(LOCK_FILE.read_text()) if LOCK_FILE.exists() else {}
    lock[script] = {name: fingerprint(tool) for name, tool in tools.items()}
    LOCK_FILE.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
    print(f"pinned {len(tools)} tools from {script}")
    return 0


async def check(script: str) -> int:
    lock = json.loads(LOCK_FILE.read_text()) if LOCK_FILE.exists() else {}
    if script not in lock:
        print(f"{script} is not pinned: run review, then pin")
        return 2
    tools = await fetch_tools(script)
    pinned = lock[script]
    problems = 0
    for name in sorted(pinned.keys() | tools.keys()):
        if name not in tools:
            print(f"REMOVED {name}")
        elif name not in pinned:
            print(f"ADDED   {name}")
            show(tools[name])
        elif fingerprint(tools[name]) != pinned[name]:
            print(f"CHANGED {name}")
            show(tools[name])
        else:
            print(f"ok      {name}")
            continue
        problems += 1
    return 1 if problems else 0


if __name__ == "__main__":
    command, script = sys.argv[1:3]
    sys.exit(asyncio.run({"review": review, "pin": pin, "check": check}[command](script)))
