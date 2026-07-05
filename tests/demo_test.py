from anthropic import Anthropic
import subprocess
import os
import dotenv


"""
get a client. API key, base url
get a meesage list. 
call LLM. include: message, model,system message, tools, max token.
append llm result to message: [{"role":"assistant","contents":[ContentBlocks]}]


how to handle the tool blocks:
check blocks type: should be tooluse.
check name to get the tool name.
check the input to get the tool(function) parameter.

run the tool and get the result. 

append the result to message: {"role":"use","type":"tool_use",contents:[""]}


3 times we append the messages list: query, llm response, tool call results.

"""

dotenv.load_dotenv()

TOOLS=[
    {"name":"bash",
     

    }
]


client=Anthropic(
    api_key=None, base_url=base_url, default_headers=default_headers
)

def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=os.getcwd(),
            capture_output=True,
            text=True,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {str(e)}"


def agent_loop(messages: list, system: str, tools: list):
    """
    Main loop for the agent. It will keep asking for user input and generate responses until the user exits.
    """
    while True:
        response = client.messages.create(
            model=MODEL,
            system=system,
            messages=messages,
            tools=tools,
        )
        if response.stop_reason != "tool_use":
            return
        
        for block in response.content:
            if block.type=="tool_use":
                tool_name = block.tool.name
                tool_input = block.tool.input
                if tool_name == "bash":
                    command = tool_input.get("command")
                    result = run_bash(command)
                    messages.append({"role": "tool", "name": tool_name, "content": result})
