# Plugin

The odctl plugin adds the [agent skill](https://jaehyeon.me/odctl/latest/ai/agent-skill/index.md) and the [MCP server](https://jaehyeon.me/odctl/latest/guides/mcp-server/index.md) to Claude Code, Codex or Antigravity with one install. The plugin starts the server as `odctl mcp`, without `--allow-changes`, so the assistant gets the five tools that only read and cannot start or stop profiles.

The repository holds the plugin's files at its root: a manifest for each tool, a marketplace file for the tools that have one, and the MCP entry. Codex copies the plugin into its cache, `~/.codex/plugins/cache/odctl/odctl/<version>/`, and Antigravity copies it to `~/.gemini/config/plugins/odctl/`, where it failed on a symlink that points outside the folder, such as one in a local clone's `.venv`. Claude Code copies a GitHub marketplace into `~/.claude/plugins/` and reads a local-path marketplace in place.

## Before You Install

The plugin does not install odctl. The MCP server it starts runs the `odctl` command, which needs the `mcp` extra, so install odctl first:

```bash
uv tool install "odctl[mcp]"
# or, if you installed odctl with pipx
pipx install --force "odctl[mcp]"
```

Without the extra, `odctl mcp` exits with an error that names this command.

## Install

Run the lines of your tool. Each installs the plugin from the repository's `main` branch.

Claude Code:

```bash
claude plugin marketplace add jaehyeon-kim/odctl
claude plugin install odctl@odctl
```

Codex:

```bash
codex plugin marketplace add jaehyeon-kim/odctl
codex plugin add odctl@odctl
```

For Claude Code and Codex, `odctl@odctl` is the plugin's name, an `@`, and the marketplace's name, which are both `odctl`.

Antigravity:

```bash
agy plugin install https://github.com/jaehyeon-kim/odctl
```

Start a new session after the install, so the tool loads the skill and the server.

## Check the Install

The skill is named `odctl:odctl` in Claude Code and Codex, which join the plugin's name and the skill's name with a colon. Antigravity uses the skill's own name, `odctl`.

- **Claude Code:** `claude plugin list` shows `odctl@odctl` as enabled, and `claude plugin details odctl` lists the skill and the MCP server.
- **Codex:** `codex plugin list` shows odctl with its status, and `/plugins` in `codex` shows it under its marketplace.
- **Antigravity:** `agy plugin list` shows the plugin, its version and its skill count, and `agy plugin list --json` lists the skill's name.

Then ask the assistant a request that needs a stack, such as "start Kafka and Flink on my machine with odctl". It loads the skill, and it can call the MCP tool `list` to read the profiles.

In print mode (`claude -p`, `agy -p`), the tool cannot ask before the assistant's first call to an MCP tool, so allow the odctl tools for the run:

- **Claude Code:** name each tool in `--allowedTools`, such as `--allowedTools mcp__plugin_odctl_odctl__list`.
- **Antigravity:** pass `--settings '{"permissions":{"allow":["mcp(odctl_odctl/list)"]}}'`, which holds for that run only.

`codex exec` called the tool without this.

## Update

A new odctl release changes the plugin's version. Update with the same tool:

- **Claude Code:** `claude plugin update odctl@odctl`.
- **Codex:** `codex plugin marketplace upgrade odctl`, which reinstalls the plugin.
- **Antigravity:** run `agy plugin install https://github.com/jaehyeon-kim/odctl` again.

## Allow Up and Down

The plugin's server is read-only. To let an assistant start and stop profiles, add `odctl mcp --allow-changes` to your tool's MCP settings by hand, as [Allow Up and Down](https://jaehyeon.me/odctl/latest/guides/mcp-server/#allow-up-and-down) explains, and read what the tools can remove first.

## Sources

The install commands are those of each tool's own help (`claude plugin install --help`, `codex plugin add --help` and `agy plugin help`), [Create a marketplace](https://code.claude.com/docs/en/plugin-marketplaces) for Claude Code, and [Plugins](https://antigravity.google/docs/plugins?tab=cli) for Antigravity.
