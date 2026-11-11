# Connect an AI Agent with MCP

MCP, the Model Context Protocol, lets an AI agent discover and call the tools of a server. A tool is a function with a name and named parameters.

`odctl mcp` starts an MCP server that offers odctl's commands as tools. An MCP client, such as an AI assistant, starts `odctl mcp` as a process. It exchanges messages with the process over its standard input and output, which MCP calls stdio. The agent calls a tool and odctl runs the command.

The server offers five tools that only read, each running the command of the same name:

- `list` returns every profile with its services and ports.
- `explain` takes `profile` and returns that profile's services, images, ports, volumes and usage.
- `ps` takes `profiles` and returns their containers and the active profiles, or every container odctl manages when `profiles` is left out.
- `info` returns the odctl version, the image tag, the workspace, whether Docker is reachable and odctl's own images.
- `logs` takes `profiles`, `service`, `tail`, `timestamps`, `since` and `until`, and returns the logs of the containers of those profiles.

`tail` defaults to 100 lines, so one call cannot fill the agent's context with a long log. `odctl logs` prints all lines, and a call can pass another number.

Results and errors:

- `list`, `explain`, `ps` and `info` return the documents on the [JSON Output](https://jaehyeon.me/odctl/latest/json-output/index.md) page, and `list`'s array arrives under the key `result` because a tool's structured result is an object.
- `info` reports Docker as not reachable with `reachable: false`, not as an error.
- `logs` returns the lines that `odctl logs` prints.
- A tool that fails returns the error message of the command.
- Tools run one at a time.

The server offers the tools `up` and `down` only when you start it with `--allow-changes`, as [Allow Up and Down](#allow-up-and-down) explains. The tool names and their parameter names stay the same in every 1.x release, as [What Stays Stable in 1.x](https://jaehyeon.me/odctl/latest/how-it-works/#what-stays-stable-in-1x) says.

This guide builds on [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md) and [JSON Output](https://jaehyeon.me/odctl/latest/json-output/index.md).

## Install

The server needs the `mcp` extra of odctl. This installs odctl with it:

```bash
uv tool install "odctl[mcp]"
```

Without the extra, `odctl mcp` exits with an error that names this command. `uv tool install` keeps odctl in an environment of its own, so the client scripts below need the `mcp` package in an environment of their own. This makes one in the current folder: `python -m venv .venv`, then `source .venv/bin/activate` and `pip install "mcp>=2.3.0,<3"`. Keep it out of an environment that holds the client of the [Feast guide](https://jaehyeon.me/odctl/latest/guides/feast-iceberg/#connect-an-mcp-client), which needs `mcp` below 2.

## Add It to an MCP Client

Claude Code is Anthropic's command-line coding agent, and it is an MCP client. The scripts in the next sections start the server themselves and need no client set up, so skip this section if you use only them. Run this in the folder of your project to add odctl to the project:

```bash
# Writes .mcp.json in this folder.
claude mcp add --scope project odctl -- odctl mcp
```

The command writes this entry to `.mcp.json`:

```json
{
  "mcpServers": {
    "odctl": {
      "type": "stdio",
      "command": "odctl",
      "args": [
        "mcp"
      ],
      "env": {}
    }
  }
}
```

Any MCP client that starts a server over stdio needs the same two things, the command `odctl` and the argument `mcp`. odctl reads the `.odctl` workspace of the folder where the client starts it. When your client starts servers in another folder, put `"--workspace", "<absolute path to .odctl>"` before `"mcp"` in the highlighted `args`. The `--workspace` option sets the workspace for every tool, because it is read once, when the server starts.

## List the Tools

This script starts the server command from its arguments and prints the name and description of each tool. Save it as `mcp_client.py` and run it in the environment that has `mcp`:

```python
import sys

import anyio
from mcp import Client, StdioServerParameters


async def main(command):
    """Print the name and description of each tool the server offers.

    Args:
        command: The command that starts the server, as a list of words.
    """
    server = StdioServerParameters(command=command[0], args=command[1:])
    async with Client(server) as client:
        for tool in (await client.list_tools()).tools:
            print(f"{tool.name}: {tool.description}")


anyio.run(main, sys.argv[1:])
```

This lists the five tools that only read:

```bash
python mcp_client.py odctl mcp
```

```text
list: List every profile with its services and ports, as `odctl list --json` does.
explain: Describe one profile: its services, images, ports, volumes and usage, as `odctl explain --json` does.
ps: Show the containers odctl manages and the active profiles, as `odctl ps --json` does. Without profiles it shows every container.
info: Show the odctl version, the image tag, the workspace, whether Docker is reachable and odctl's images, as `odctl info --json` does.
logs: Fetch the logs of the containers of some profiles, as `odctl logs` prints them, the last 100 lines of each by default.
```

## Allow Up and Down

The tools `up` and `down` start and stop profiles, so an agent that can call them changes what runs on your machine. They exist only when the server starts with the option `--allow-changes`. An option shows in the client's configuration, where an environment variable left set in a shell could allow changes without anyone seeing it. This lists the seven tools:

```bash
python mcp_client.py odctl mcp --allow-changes
```

```text
list: List every profile with its services and ports, as `odctl list --json` does.
explain: Describe one profile: its services, images, ports, volumes and usage, as `odctl explain --json` does.
ps: Show the containers odctl manages and the active profiles, as `odctl ps --json` does. Without profiles it shows every container.
info: Show the odctl version, the image tag, the workspace, whether Docker is reachable and odctl's images, as `odctl info --json` does.
logs: Fetch the logs of the containers of some profiles, as `odctl logs` prints them, the last 100 lines of each by default.
up: Start profiles and their dependencies, as `odctl up` does.
down: Stop the named profiles. With `volumes`, also remove their volumes, and the shared jar volume `odctl-shared-deps` once no other profile has a container, as `odctl down --volumes` does.
```

`up` takes `profiles` and `pull`, and `down` takes `profiles` and `volumes`. Each returns what the command prints. The server marks both as destructive, so a client can ask before it runs them. `up` replaces a container whose definition changed, and the data inside it goes with it. `down` takes named profiles only. `odctl down --all --volumes` asks before it removes the data of every profile, and a server cannot ask. So `down` with `volumes` refuses names that cover every profile `odctl down --all --volumes` would stop, and no tool removes everything in one call.

## Runnable Example

Save this file as `example.py` and run it with `python example.py` in the folder that holds your `.odctl` workspace, made by `odctl init` as [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/index.md) shows, in the environment that has `mcp`. It starts the server with `--allow-changes`, starts `kafka-lite`, reads `info`, the containers of `kafka-lite` and the last five lines of the `connect` service, then stops `kafka-lite`. A tool that fails returns its error as the result, so the script checks each result, stops at the first error and still stops `kafka-lite`:

```python
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
```

It prints the result of each tool under a line with the tool's name. The output below shortens the path of the `.odctl` folder to `/home/you/project/.odctl`:

```text
--- up
⚙️  Launching 🧱 Infrastructure (deps)...
⚙️  Launching 🚀 Target (kafka-lite)...
✓ All requested profiles successfully started!
--- info
{
  "cli_version": "1.6.0",
  "tag": "1.6.0",
  "workspace": {
    "path": "/home/you/project/.odctl",
    "exists": true,
    "stale_tag": null
  },
  "docker": {
    "reachable": true
  },
  "images": [
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/airflow:1.6.0",
      "local": false
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/deps:1.6.0",
      "local": true
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/mlflow:1.6.0",
      "local": false
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/postgres:1.6.0",
      "local": false
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/spark:1.6.0",
      "local": false
    }
  ]
}
--- ps
{
  "active_profiles": [
    "kafka-lite"
  ],
  "containers": [
    {
      "name": "connect",
      "service": "connect",
      "state": "running",
      "health": null,
      "ports": [
        {
          "host": 8083,
          "container": 8083,
          "protocol": "tcp"
        }
      ]
    },
    {
      "name": "kafka",
      "service": "kafka",
      "state": "running",
      "health": null,
      "ports": [
        {
          "host": 9092,
          "container": 9092,
          "protocol": "tcp"
        }
      ]
    },
    {
      "name": "kafka-ui",
      "service": "kafka-ui",
      "state": "running",
      "health": null,
      "ports": [
        {
          "host": 8086,
          "container": 8080,
          "protocol": "tcp"
        }
      ]
    },
    {
      "name": "karapace",
      "service": "karapace",
      "state": "running",
      "health": "healthy",
      "ports": [
        {
          "host": 8081,
          "container": 8081,
          "protocol": "tcp"
        }
      ]
    }
  ]
}
--- logs
connect  | [2026-10-30 21:50:24,917] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] Cluster ID: 42RglGpZQwy9D5VzTVpCWA (org.apache.kafka.clients.Metadata:365)
connect  | [2026-10-30 21:50:24,919] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] Discovered group coordinator broker-1:19092 (id: 2147483646 rack: null isFenced: false) (org.apache.kafka.connect.runtime.distributed.WorkerCoordinator:943)
connect  | [2026-10-30 21:50:24,920] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] Rebalance started (org.apache.kafka.connect.runtime.distributed.WorkerCoordinator:239)
connect  | [2026-10-30 21:50:24,920] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] (Re-)joining group (org.apache.kafka.connect.runtime.distributed.WorkerCoordinator:611)
connect  | [2026-10-30 21:50:24,923] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] (Re-)joining group (org.apache.kafka.connect.runtime.distributed.WorkerCoordinator:611)
--- down
🛑 Stopping kafka-lite...
✓ Teardown complete.
```
