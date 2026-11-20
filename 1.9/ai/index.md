# AI Assistants

An AI coding assistant can start and use an odctl stack when it has three things: the rules for choosing profiles and reaching their services, odctl's commands as tools it can call, and odctl's documentation as text. This section describes each and how to install them.

The parts relate as follows:

| Part        | What it gives the assistant                                                                                                                                                                     | Page                                                                      |
| ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Agent skill | a folder, `skills/odctl/`, of rules in the Agent Skills format: which profile to start, how to reach each service from the host and from a container, and how to run odctl in a project's tests | [Agent Skill](https://jaehyeon.me/odctl/latest/ai/agent-skill/index.md)   |
| MCP server  | `odctl mcp`, which offers odctl's commands to an MCP client as tools; MCP, the Model Context Protocol, is the standard an assistant uses to call a tool                                         | [MCP Server](https://jaehyeon.me/odctl/latest/guides/mcp-server/index.md) |
| Plugin      | one install for Claude Code, Codex or Antigravity that adds the skill and the MCP server together                                                                                               | [Plugin](https://jaehyeon.me/odctl/latest/ai/plugin/index.md)             |
| `llms.txt`  | the pages of this site as text, for an assistant that reads documentation                                                                                                                       | below                                                                     |

The plugin is a package of the other two parts. It starts the MCP server read-only, so the assistant can list, explain, inspect and read logs, and cannot run `up` or `down`. Install the skill without the plugin when your tool has no plugin support, and set up the MCP server by hand to allow `up` and `down`. The plugin does not install odctl, and its MCP server needs the `mcp` extra: see [Before You Install](https://jaehyeon.me/odctl/latest/ai/plugin/#before-you-install).

## Documentation as Text

The site publishes two files built from the sidebar:

- [`llms.txt`](https://jaehyeon.me/odctl/llms.txt) is an index of the pages with a link to each.
- [`llms-full.txt`](https://jaehyeon.me/odctl/llms-full.txt) holds every page in one file.

Give an assistant one of them when its tool cannot install a skill. The skill is shorter and tells the assistant what to do, while the pages describe every profile and command.
