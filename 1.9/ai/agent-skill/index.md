# Agent Skill

The odctl skill gives an AI coding assistant the rules for using odctl, so it starts the right profiles, reaches their services at the right address and stops only what it started, instead of guessing.

A skill is a folder in the Agent Skills format that Claude Code, Codex and other assistants read. The assistant loads the skill when a request needs one of the technologies odctl runs locally, such as Kafka, Spark, Trino or MLflow, or code that connects to them.

The folder is `skills/odctl/` in the repository:

| File                     | What it covers                                                                                                                                                                                                       |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SKILL.md`               | a checklist for the assistant to copy into its reply; the rules for starting, waiting for, stopping and reaching services, each with a wrong and a right example; and the commands, options and `.env` keys of odctl |
| `references/profiles.md` | for each profile, its addresses from the host and from a container, its logins, what `odctl up` also starts, its services, ports and memory limits, which services `odctl up` waits for, and where its data lives    |
| `references/testing.md`  | odctl in a project's tests and CI: pinning the version, starting and stopping the profiles a job needs, and what a teardown removes                                                                                  |

The commands, options, keys and profile notes are generated from odctl's CLI, `registry.yml` and compose files, so the folder lists what the release has. The rules and `references/testing.md` are written by hand in `scripts/skill/`.

The skill does not install odctl or Docker. The assistant runs the `odctl` commands, so install odctl first, as [Getting Started](https://jaehyeon.me/odctl/latest/getting-started/#install) shows.

## Install with the Plugin

The [plugin](https://jaehyeon.me/odctl/latest/ai/plugin/index.md) installs the skill for Claude Code, Codex and Antigravity, together with the MCP server.

## Install without the Plugin

Copy `skills/odctl/` into the skills folder of your assistant. Take it from the repository at the tag of the release you installed, which is `v` followed by the `cli_version` that `odctl info --json` prints. For Claude Code, `~/.claude/skills/odctl/` is for every project and `.claude/skills/odctl/` in a project is for that project. These lines copy it for every project:

```bash
# The source of the installed release, which holds the skill
version=$(odctl info --json | python3 -c 'import json, sys; print(json.load(sys.stdin)["cli_version"])')
src=$(mktemp -d)
git clone --depth 1 --branch "v$version" https://github.com/jaehyeon-kim/odctl "$src" &&
  mkdir -p ~/.claude/skills &&
  rm -rf ~/.claude/skills/odctl &&
  cp -R "$src/skills/odctl" ~/.claude/skills/odctl
rm -rf "$src"
```

The lines clone into a new private folder, replace an earlier copy of the skill only when the clone succeeds, and remove the clone, so they also update the skill to a newer release. If `CLAUDE_CONFIG_DIR` is set, use that folder in place of `~/.claude`.

With the GitHub CLI 2.90.0 or later, one command does the copy. Without `--pin`, it takes the latest tagged release, which can be newer than the odctl you installed, so the lines pin the installed release:

```bash
# The release that is installed
version=$(odctl info --json | python3 -c 'import json, sys; print(json.load(sys.stdin)["cli_version"])')
gh skill install jaehyeon-kim/odctl odctl --pin "v$version" --agent claude-code --scope user
```

`--scope user` installs for every project, in your home folder. `--scope project`, the default, installs for the current project, inside its git repository. Another assistant takes its own `--agent` value, listed in `gh skill install --help`.

## Check the Install

Check that the folder holds `SKILL.md`:

```bash
ls ~/.claude/skills/odctl/SKILL.md
```

In Claude Code, `/skills` lists the loaded skills, and `odctl` must be among them. After a project copy, check `.claude/skills/odctl/SKILL.md` in the project instead.

Then ask the assistant for a stack, such as "run Kafka and Flink on my machine with odctl". It reads the skill when the request names one of the technologies.

## Limits

- The skill's rules cover odctl's container lifecycle: starting, waiting, stopping, addresses and logins.
- `references/testing.md` covers how a test starts odctl's stack, not what the tests check.
