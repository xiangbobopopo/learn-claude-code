#!/usr/bin/env python3
# Harness: tool dispatch -- expanding what the model can reach.
"""
s02_tool_use.py - Tools

The agent loop from s01 didn't change. We just added tools to the array
and a dispatch map to route calls.

    +----------+      +-------+      +------------------+
    |   User   | ---> |  LLM  | ---> | Tool Dispatch    |
    |  prompt  |      |       |      | {                |
    +----------+      +---+---+      |   bash: run_bash |
                          ^          |   read: run_read |
                          |          |   write: run_wr  |
                          +----------+   edit: run_edit |
                          tool_result| }                |
                                     +------------------+

Key insight: "The loop didn't change at all. I just added tools."
"""

import os
import subprocess
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
api_key = os.getenv("ANTHROPIC_API_KEY")
base_url = os.getenv("ANTHROPIC_BASE_URL")

# For LongCat, we need to use custom headers with Bearer token
default_headers = {"Authorization": f"Bearer {api_key}"}
client = Anthropic(
    api_key=None, base_url=base_url, default_headers=default_headers
)
MODEL = os.environ["MODEL_ID"]

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks. Act, don't explain."


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_system_info(category: str = "all") -> str:
    try:
        import platform
        import datetime
        import os

        info = []
        info.append(f"=== System Information ({category}) ===")
        info.append(f"Timestamp: {datetime.datetime.now()}")

        if category in ["all", "system"]:
            info.append(f"\nSystem: {platform.system()} {platform.release()}")
            info.append(f"Machine: {platform.machine()}")
            info.append(f"Processor: {platform.processor()}")
            info.append(f"Python: {platform.python_version()}")

        # Try to get more detailed system info if psutil is available
        try:
            import psutil
            if category in ["all", "cpu"]:
                info.append(f"\nCPU: {psutil.cpu_count(logical=False)} cores, {psutil.cpu_count(logical=True)} threads")
                info.append(f"CPU Usage: {psutil.cpu_percent(interval=1)}%")

            if category in ["all", "memory"]:
                memory = psutil.virtual_memory()
                info.append(f"\nMemory: {memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB ({memory.percent}% used)")

            if category in ["all", "disk"]:
                disk = psutil.disk_usage('/')
                info.append(f"\nDisk: {disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB ({disk.percent}% used)")
        except ImportError:
            info.append("\nNote: Install 'psutil' for detailed CPU/Memory/Disk info")

        return "\n".join(info)
    except Exception as e:
        return f"Error: {e}"


def run_hash_file(path: str, algorithm: str = "sha256") -> str:
    try:
        import hashlib

        fp = safe_path(path)
        if not fp.exists():
            return f"Error: File not found: {path}"

        hash_func = getattr(hashlib, algorithm.lower(), None)
        if not hash_func:
            return f"Error: Unsupported algorithm: {algorithm}"

        with open(fp, 'rb') as f:
            file_hash = hashlib.new(algorithm.lower())
            chunk = f.read(8192)
            while chunk:
                file_hash.update(chunk)
                chunk = f.read(8192)

        return f"{algorithm.upper()}: {file_hash.hexdigest()}\nFile: {path}\nSize: {fp.stat().st_size} bytes"
    except Exception as e:
        return f"Error: {e}"


# -- The dispatch map: {tool_name: handler} --
TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "system_info": lambda **kw: run_system_info(kw.get("category", "all")),
    "hash_file": lambda **kw: run_hash_file(kw["path"], kw.get("algorithm", "sha256")),
}

TOOLS = [
    {
        "name": "bash",
        "description": "Run a shell command.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read file contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact text in file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "system_info",
        "description": "Get system information (CPU, memory, disk, etc.)",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["all", "system", "cpu", "memory", "disk"],
                    "description": "Type of system info to retrieve"
                }
            },
            "required": [],
        },
    },
    {
        "name": "hash_file",
        "description": "Calculate file hash using specified algorithm",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "algorithm": {
                    "type": "string",
                    "enum": ["md5", "sha1", "sha256", "sha512"],
                    "description": "Hash algorithm to use"
                }
            },
            "required": ["path"],
        },
    },
]


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model=MODEL,
            system=SYSTEM,
            messages=messages,
            tools=TOOLS,
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOL_HANDLERS.get(block.name)
                output = (
                    handler(**block.input)
                    if handler
                    else f"Unknown tool: {block.name}"
                )
                print(f"> {block.name}:")
                print(output[:200])
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": output,
                    }
                )
        messages.append({"role": "user", "content": results})


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms02 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in {"q", "exit", ""}:
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()
