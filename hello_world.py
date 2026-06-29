from anthropic import Anthropic


client=Anthropic()


def run_bash():
    ...


def agent_loop(messages:list):
    while True:
        response=client.messages.create(
            
        )

        messages.append({"role":"assistant","content":response.content})
        for block in response.contents:
            if block.type=="tool_use":
                out_put=run_bash(block.input["command"])

            messages.append({"role":"user","content":out_put})
