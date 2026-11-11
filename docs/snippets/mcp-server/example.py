import os

import anyio
from mcp import Client, StdioServerParameters


async def call(client, name, arguments):
    """Call one tool, print its name and its text result, and stop on an error.

    A tool that fails returns its error as the result, so the call checks for it.

    Args:
        client: The connected MCP client.
        name: The tool to call.
        arguments: The tool's parameters.

    Raises:
        RuntimeError: When the tool returns an error.
    """
    result = await client.call_tool(name, arguments)
    print(f"--- {name}")
    print(result.content[0].text)
    if result.is_error:
        raise RuntimeError(f"the tool {name} failed")


async def main():
    """Start kafka-lite, read it through four tools, then stop it."""
    # Docker reads variables such as DOCKER_HOST, which a client passes to the
    # server only when asked.
    server = StdioServerParameters(
        command="odctl", args=["mcp", "--allow-changes"], env=dict(os.environ)
    )
    async with Client(server) as client:
        try:
            await call(client, "up", {"profiles": ["kafka-lite"]})
            await call(client, "info", {})
            await call(client, "ps", {"profiles": ["kafka-lite"]})
            await call(client, "logs", {"profiles": ["kafka-lite"], "service": "connect", "tail": 5})
        finally:
            # Stop kafka-lite even when a tool failed.
            await call(client, "down", {"profiles": ["kafka-lite"]})


anyio.run(main)
