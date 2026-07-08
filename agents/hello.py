from anthropic import Anthropic
import subprocess
from pathlib import Path

client = Anthropic(base_url="")


def run_bash(cmd: str):
    r = subprocess.run(
        cmd=cmd,
        cwd=Path.cwd(),
        shell=True,
        text=True,
        capture_output=True,
        timeout=120
    )
    out = (r.stdout + r.stderr).strip()
    return out


TOOLS = [{"name": "run_bash",
          "description": "run shell command",
          "input_schema": {
              "type": "object",
              "properties": {"cmd": {"type": "string"}},
              "required": ["cmd"]
          }
          }]

TOOLS_HANDLER = {"run_bash": lambda **kw: run_bash(kw["cmd"])}


def agent_loop(messages: list):
    while True:
        response = client.messages.create(
            model="",
            system="",
            tools=tools,
            messages=messages,
            max_tokens=2000
        )
        if response.stop_reason != "tool_use":
            return
        messages.append({"assistant": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = TOOLS_HANDLER.get(block.name)
                output = handler(**block.input)
            results.append({
                "type": "tool_use",
                "tool_use_id": block.tool_use_id,
                "content": output[:2000]
            })
        messages.append({"role": "user", "content": results})
