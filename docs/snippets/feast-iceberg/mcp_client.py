import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main():
    async with streamable_http_client("http://127.0.0.1:6566/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for tool in (await session.list_tools()).tools:
                print(tool.name)
            result = await session.call_tool(
                "get_online_features_get_online_features_post",
                {"features": ["driver_pushed:conv_rate"], "entities": {"driver_id": [1001]}},
            )
            if result.isError:
                return result.content[0].text
            reply = json.loads(result.content[0].text)
            names = reply["metadata"]["feature_names"]
            print(reply["results"][names.index("conv_rate")]["values"])


error = asyncio.run(main())
if error:
    raise SystemExit(error)
