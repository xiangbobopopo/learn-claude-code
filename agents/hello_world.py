#!/usr/bin/env python3
# Hello World Program
from anthropic import Anthropic

client = Anthropic()

MODEL = ""
SYSTEM = ""
TOOLS = [
    {"name": "bash",
     "description": "run a bash command",
     "input_schema": {
         "type": "object",
         "properties": {
             "command": {"type": "string"}
         },
         "required": ["command"]}
     }
]

TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "run_delete": lambda **kwargs: run_delete(kwargs["delete_command"])
}


def run_bash(command: str):
    ...


def run_delete(delete_command: str):
    ...


def agent_loop(message: list):
    while True:
        response = client.messages.create(
            model=MODEL
            , system=SYSTEM
            , messages=message
            , tools=TOOLS
        )
        message.append({"role": "assistant", "contents": response.content})
        if response.stop_reason != "tool_use":
            return
        results = []
        for block in response.content:
            handler = TOOL_HANDLERS.get(block.name)
            result = handler(**block.input) if handler else f"Unknown tool: {block.name}"
            results.append(
                {"type": "tool_use",
                 "tool_use_id": block.id,
                 "content": result}
            )
        message.append({"role": "user", "content": results})
