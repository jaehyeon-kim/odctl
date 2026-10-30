# Connect an AI Agent with MCP

MCP, the Model Context Protocol, lets an AI agent discover and call the tools of a server. A tool is a function with a name and named parameters. `odctl mcp` starts an MCP server that offers odctl's commands as tools. The client, such as an AI assistant, starts `odctl mcp` as a process and exchanges messages with it over stdio, the process's standard input and output. The agent calls a tool and odctl runs the command.

The server offers five tools that only read, each running the command of the same name:

- `list` returns every profile with its services and ports.
- `explain` returns one profile's services, images, ports, volumes and usage. It takes `profile`.
- `ps` returns the containers odctl manages and the active profiles. It takes `profiles`, and without it returns every container.
- `info` returns the odctl version, the image tag, the workspace, whether Docker is reachable and odctl's own images.
- `logs` returns the logs of the containers of some profiles. It takes `profiles`, `service`, `tail`, `timestamps`, `since` and `until`. `tail` defaults to 100 lines, where `odctl logs` prints all of them, so one call cannot fill the agent's context with a long log. A call can pass another number.

Results and errors:

- `list`, `explain`, `ps` and `info` return the documents on the [JSON Output](../json-output.md) page. A structured result of a tool is an object, so the array of `list` arrives under the key `result`.
- `info` reports Docker as not reachable with `reachable: false`, not as an error.
- `logs` returns the lines that `odctl logs` prints.
- A tool that fails returns the error message of the command.
- Tools run one at a time.

The tools `up` and `down` are served only when you start the server with `--allow-changes`, as [Allow Up and Down](#allow-up-and-down) explains. The tool names and their parameter names stay the same in every 1.x release, as [What Stays Stable in 1.x](../how-it-works.md#what-stays-stable-in-1x) says.

This guide builds on [Getting Started](../getting-started.md) and [JSON Output](../json-output.md).

## Install

The server needs the `mcp` extra of odctl. This installs odctl with it:

```bash title="docs/snippets/mcp-server/commands.sh:install"
uv tool install "odctl[mcp]"
```

Without the extra, `odctl mcp` exits with an error that names this command. `uv tool install` keeps odctl in an environment of its own, so the client script below needs the `mcp` package in yours: `pip install "mcp>=2.3.0,<3"`. Keep it out of an environment that holds the client of the [Feast guide](feast-iceberg.md#connect-an-mcp-client), which needs `mcp` below 2.

## Add It to an MCP Client

Claude Code is Anthropic's command-line coding agent, and it is an MCP client. Run this in the folder of your project to add odctl to the project:

```bash title="docs/snippets/mcp-server/commands.sh:claude-code"
# Writes .mcp.json in this folder.
claude mcp add --scope project odctl -- odctl mcp
```

The command writes this entry to `.mcp.json`:

```json title="docs/snippets/mcp-server/mcp.json" hl_lines="6-8"
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

```python title="docs/snippets/mcp-server/mcp_client.py"
import sys

import anyio
from mcp import Client, StdioServerParameters


async def main(command):
    server = StdioServerParameters(command=command[0], args=command[1:])
    async with Client(server) as client:
        for tool in (await client.list_tools()).tools:
            print(f"{tool.name}: {tool.description}")


anyio.run(main, sys.argv[1:])
```

This lists the five tools that only read:

```bash title="docs/snippets/mcp-server/commands.sh:list-tools"
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

```bash title="docs/snippets/mcp-server/commands.sh:list-tools-changes"
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

`up` takes `profiles` and `pull`, and `down` takes `profiles` and `volumes`. Each returns what the command prints. `up` and `down` are marked as destructive, which a client can use to ask before it runs them: `up` replaces a container whose definition changed, and the data inside it goes with it. `down` takes named profiles only: `odctl down --all --volumes` asks before it removes the data of every profile, and a server cannot ask, so no tool removes everything in one call.

## Runnable Example

Save this file as `example.py` and run it with `python example.py` in the folder that holds your `.odctl` workspace, in the environment that has `mcp`. It starts the server with `--allow-changes`, starts `kafka-lite`, reads `info`, the containers of `kafka-lite` and the last five lines of the `connect` service, then stops `kafka-lite`:

```python title="docs/snippets/mcp-server/example.py"
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
```

It prints the result of each tool under a line with the tool's name:

```text
--- up
⚙️  Launching 🧱 Infrastructure (deps)...
⚙️  Launching 🚀 Target (kafka-lite)...
✓ All requested profiles successfully started!
--- info
{
  "cli_version": "1.5.0",
  "tag": "1.5.0",
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
      "reference": "ghcr.io/jaehyeon-kim/odctl/airflow:1.5.0",
      "local": false
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/deps:1.5.0",
      "local": true
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/mlflow:1.5.0",
      "local": false
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/postgres:1.5.0",
      "local": true
    },
    {
      "reference": "ghcr.io/jaehyeon-kim/odctl/spark:1.5.0",
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
connect  | [2026-10-30 17:53:43,681] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] Herder started (org.apache.kafka.connect.runtime.distributed.DistributedHerder:388)
connect  | [2026-10-30 17:53:43,681] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] Starting connectors and tasks using config offset -1 (org.apache.kafka.connect.runtime.distributed.DistributedHerder:1960)
connect  | [2026-10-30 17:53:43,682] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] Finished starting connectors and tasks (org.apache.kafka.connect.runtime.distributed.DistributedHerder:1989)
connect  | [2026-10-30 17:53:43,718] INFO [Worker clientId=connect-connect:8083, groupId=odctl-connect-cluster] Session key updated (org.apache.kafka.connect.runtime.distributed.DistributedHerder:2490)
connect  | [2026-10-30 17:54:07,279] INFO 192.168.107.5 - - [30/Oct/2026:17:54:07 +0000] "GET /connectors?expand=info&expand=status HTTP/1.1" 200 2 "" "ReactorNetty/1.2.16" 38 (org.apache.kafka.connect.runtime.rest.RestServer:57)
--- down
🛑 Stopping kafka-lite...
✓ Teardown complete.
```
