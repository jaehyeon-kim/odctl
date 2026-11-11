# Getting Started

This page installs odctl, starts a first profile, runs each command on it and stops it. It needs no earlier page. The recording shows the main steps: install odctl, preview a profile, start it, list the containers and stop them.

## Requirements

- Docker Engine or Docker Desktop, running. Give Docker 8 to 16 GB of memory.
- Python 3.10 or later.

## Install

odctl is a command-line tool, so install it into its own environment with uv or pipx:

```bash
uv tool install odctl
# or
pipx install odctl
```

`pip install odctl` also works. `odctl --help` then lists the commands.

## Create a Workspace

Run this in the folder of your project:

```bash
odctl init
```

It prints `Workspace initialized!` with the path of the new folder. The command copies the compose files and their settings into `.odctl` in the current directory, and writes `.odctl/.env` with `TAG` set to the CLI version. odctl reads from `.odctl` whenever it exists, so you can edit any file there. [Workspace](https://jaehyeon.me/odctl/latest/how-it-works/#workspace) explains what changes with and without it, and how to customise it.

## Start a Profile

A [profile](https://jaehyeon.me/odctl/latest/how-it-works/#profiles) is a named group of services that start together. This lists every profile, with its parent stack and a description:

```bash
odctl list
```

Add `-d` to list each profile's services and host ports as well:

```bash
odctl list -d
```

Add `--json` to print the profiles as JSON, which a script or an AI assistant reads more easily than a table. odctl prints the JSON on standard output and every warning on standard error, so a pipe receives only the JSON. The warning for a stale workspace is one example. The full output is an array with one object for each profile, and this keeps only `kafka-lite`:

```bash
# Print only kafka-lite; the full output lists every profile.
odctl list --json | python3 -c 'import json, sys; profiles = {p["profile"]: p for p in json.load(sys.stdin)}; print(json.dumps(profiles["kafka-lite"], indent=4))'
```

```text
{
    "profile": "kafka-lite",
    "stack": "kafka",
    "description": "Distributed event streaming and schema registry. Lite uses 1 Broker; Full uses 3 Brokers.",
    "compose_file": "compose-kafka.yml",
    "depends_on": [
        "deps"
    ],
    "starts": [
        "deps",
        "kafka-lite"
    ],
    "services": [
        {
            "name": "connect",
            "image": "apache/kafka:4.3.2",
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
            "image": "apache/kafka:4.3.2",
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
            "image": "ghcr.io/kafbat/kafka-ui:v1.5.0",
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
            "image": "ghcr.io/aiven-open/karapace:6.2.4",
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
```

Each profile is one object, and `starts` lists the profiles that `odctl up kafka-lite` starts. [JSON Output](https://jaehyeon.me/odctl/latest/json-output/index.md) lists the keys of every command that takes `--json`.

This shows what one profile runs:

```bash
odctl explain kafka-lite
```

It prints a panel for `kafka-lite`: the parent stack `kafka`, the compose file, the profile it requires (`deps`), the containers `connect`, `kafka`, `kafka-ui` and `karapace` with their images, the host ports and how to reach each service.

`--json` prints the same details as one object, with `usage`, `role` and `volumes` added to the keys of `list`. `usage` is text for people to read, not a value to parse:

```bash
odctl explain kafka-lite --json | python3 -m json.tool
```

```text
{
    "profile": "kafka-lite",
    "stack": "kafka",
    "description": "Distributed event streaming and schema registry. Lite uses 1 Broker; Full uses 3 Brokers.",
    "compose_file": "compose-kafka.yml",
    "depends_on": [
        "deps"
    ],
    "starts": [
        "deps",
        "kafka-lite"
    ],
    "services": [
        {
            "name": "connect",
            "image": "apache/kafka:4.3.2",
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
            "image": "apache/kafka:4.3.2",
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
            "image": "ghcr.io/kafbat/kafka-ui:v1.5.0",
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
            "image": "ghcr.io/aiven-open/karapace:6.2.4",
            "ports": [
                {
                    "host": 8081,
                    "container": 8081,
                    "protocol": "tcp"
                }
            ]
        }
    ],
    "usage": "\u2022 Kafka UI:\n  - External (host): http://127.0.0.1:8086\n  - Internal (Docker): http://kafka-ui:8080\n\u2022 Schema Registry & Connect:\n  - External (host): http://127.0.0.1:8081 / http://127.0.0.1:8083\n\u2022 Bootstrap Servers (1-Node Lite):\n  - External (host): 127.0.0.1:9092\n  - Internal (Docker): broker-1:19092\n",
    "role": "KRaft broker(s) with Aiven Karapace for Avro/JSON schema validation and Connect for data ingestion.",
    "volumes": []
}
```

This shows the profiles `kafka-lite` would start, in order, without starting anything:

```bash
odctl up kafka-lite --dry-run
```

The dry run prints which compose files and profiles it would start:

Start it:

```bash
odctl up kafka-lite
```

odctl starts the profiles `kafka-lite` depends on first, then Kafka. It waits until the services are running, and healthy where they define a health check, then prints `All requested profiles successfully started!`. The [Messaging page](https://jaehyeon.me/odctl/latest/profiles/messaging/#kafka-lite) lists the same addresses as `odctl explain`.

## See What Is Running

This prints the installed CLI version and whether Docker is reachable:

```bash
odctl info
```

The output has a title line, `Open Data Stack (ODCTL)`, then `CLI Version:` with the version and `Docker Daemon: ✅ Reachable`. With `--json`, it also prints the image tag, the workspace and odctl's own images, and whether each image is already on your machine. `workspace.path` is the `.odctl` folder in the folder where you run odctl; the output below shortens it to `/home/you/project/.odctl`:

```bash
odctl info --json | python3 -m json.tool
```

```text
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
```

`stale_tag` is `null` unless the workspace's `TAG` differs from the CLI version and no `TAG` is set in the shell; then it shows the workspace's `TAG`.

This lists the containers of a profile, with their state, health and ports:

```bash
odctl ps kafka-lite
```

It prints the active profiles, then a table with one row per container:

```text
🌟 Active Profiles: kafka-lite

┏━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Container ┃ Service  ┃ State   ┃ Health  ┃ Ports           ┃
┡━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ connect   │ connect  │ running │ -       │ 8083 → 8083/tcp │
│ kafka     │ kafka    │ running │ -       │ 9092 → 9092/tcp │
│ kafka-ui  │ kafka-ui │ running │ -       │ 8086 → 8080/tcp │
│ karapace  │ karapace │ running │ healthy │ 8081 → 8081/tcp │
└───────────┴──────────┴─────────┴─────────┴─────────────────┘
```

A dash under Health means the service has no health check.

`--json` prints the same containers as one object. Like the table, it needs profile names or `--all`. Each published port gives its host and container port as numbers, and a missing health check is `null`. `active_profiles` lists the profiles you named whose services are all running, with their prerequisites from the same compose file. It never holds `deps`, and it leaves out a profile whose services all belong to another listed profile, such as `spark-lite` beside `spark-full`:

```bash
odctl ps kafka-lite --json | python3 -m json.tool
```

```text
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
```

This lists every container odctl manages, from every profile, including one-shot containers that have finished, such as `odctl-init-deps`:

```bash
odctl ps --all
```

This prints the last three log lines of one service, `connect`:

```bash
odctl logs kafka-lite -s connect -n 3
```

Each line starts with the service name, such as `connect | [2026-10-24 05:14:03,065] INFO [Worker clientId=connect-connect:8083, ...`. Leave out `-s connect` to read every service of the profile, and add `-f` to follow the logs until you press Ctrl+C. This prints the last two lines written between ten minutes and one second ago, each with a timestamp before it:

```bash
odctl logs kafka-lite -s connect --since 10m --until 1s -t -n 2
```

`--since` and `--until` each take a time such as `2026-10-24T05:00:00` or a duration before now such as `10m`.

## Restart a Profile

This restarts the profile's containers and keeps them, with their data:

```bash
odctl restart kafka-lite
```

It prints `Restarting containers...` and `Restart complete.` A restart does not apply an edit to a compose file or `.env`. `odctl recreate` replaces the containers to apply one, as [Apply a Change](https://jaehyeon.me/odctl/latest/how-it-works/#apply-a-change) explains with [examples](https://jaehyeon.me/odctl/latest/how-it-works/#examples). `odctl pull` downloads a profile's images before you start it, as [Which Images Run](https://jaehyeon.me/odctl/latest/how-it-works/#which-images-run) shows.

## Stop a Profile

This prints what `odctl down` would stop, without stopping anything:

```bash
odctl down kafka-lite --dry-run
```

With `--volumes`, the dry run also lists the named volumes that `odctl down --volumes` would remove, and adds a line for each container it stops that has unnamed volumes, with their number:

```bash
odctl down kafka-lite --volumes --dry-run
```

```text
╭──────────────────────────────────────────────────────────────────────────────╮
│ Dry Run Teardown Plan                                                        │
╰──────────────────────────────────────────────────────────────────────────────╯
🛑 compose-kafka.yml
  └─ 💥 Stop Profile: kafka-lite
  └─ 🗑  Remove Volume: 3 unnamed volume(s) of connect
  └─ 🗑  Remove Volume: 3 unnamed volume(s) of kafka
🛑 compose-deps.yml
  └─ 💥 Stop Profile: deps
  └─ 🗑  Remove Volume: odctl-shared-deps
```

`kafka-lite` has no named volume of its own, and no other profile has a container, so the only named volume listed is the shared jar volume `odctl-shared-deps`. The dry run reads each container's volumes from Docker, so `connect` and `kafka` show their three unnamed volumes each, and a container with none, such as `karapace`, gets no line. Without Docker the dry run cannot count them, and says so. `odctl down --volumes` removes the shared jar volume with the last profile, and the unnamed volumes with their containers, as [Where Data Lives](https://jaehyeon.me/odctl/latest/how-it-works/#where-data-lives) explains.

This stops the profile and removes its containers:

```bash
odctl down kafka-lite
```

It prints `Teardown complete.` The data inside the containers goes with them, as [Where Data Lives](https://jaehyeon.me/odctl/latest/how-it-works/#where-data-lives) explains. It leaves the profiles that `kafka-lite` depends on in place, as [Which Containers a Command Touches](https://jaehyeon.me/odctl/latest/how-it-works/#which-containers-a-command-touches) explains. This stops every profile and also removes the named volumes, such as the shared jar volume `odctl-shared-deps`. It asks `Are you sure?` first, and stops only after you answer `y`:

```bash
odctl down --all --volumes
```

In a script, `--yes` answers the prompt:

```bash
odctl down --all --volumes --yes
```

## Code in the Guides

Every command and file in these pages is kept in the repository under [`docs/snippets`](https://github.com/jaehyeon-kim/odctl/tree/v1.6.0/docs/snippets), one folder per page, and the end-to-end tests run it on every release. A code block whose title names a file is a copy of that file, or of the section after the colon. The links on the published site point at the release that the docs describe.

## Use It with an AI Assistant

The docs site publishes [`llms.txt`](https://jaehyeon.me/odctl/llms.txt), an index of these pages for AI assistants, and `llms-full.txt` with every page in one file. The repository also has an odctl skill in [`skills/odctl/SKILL.md`](https://github.com/jaehyeon-kim/odctl/blob/v1.6.0/skills/odctl/SKILL.md), generated from the profiles, which tells an assistant which profile to start and how to reach each service. For Claude Code, copy the `skills/odctl` folder into `~/.claude/skills/`. With the `mcp` extra, `odctl mcp` gives an MCP client odctl's commands as tools, as [MCP Server](https://jaehyeon.me/odctl/latest/guides/mcp-server/index.md) sets up.
