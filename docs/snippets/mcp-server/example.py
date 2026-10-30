import os

import anyio
from mcp import Client, StdioServerParameters


async def call(client, name, arguments):
    result = await client.call_tool(name, arguments)
    print(f"--- {name}")
    print(result.content[0].text)


async def main():
    # Docker reads variables such as DOCKER_HOST, which a client passes to the
    # server only when asked.
    server = StdioServerParameters(
        command="odctl", args=["mcp", "--allow-changes"], env=dict(os.environ)
    )
    async with Client(server) as client:
        await call(client, "up", {"profiles": ["kafka-lite"]})
        await call(client, "info", {})
        await call(client, "ps", {"profiles": ["kafka-lite"]})
        await call(client, "logs", {"profiles": ["kafka-lite"], "service": "connect", "tail": 5})
        await call(client, "down", {"profiles": ["kafka-lite"]})


anyio.run(main)
