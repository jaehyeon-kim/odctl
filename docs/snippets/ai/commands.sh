# Commands from docs/ai/*.md. smoke.sh runs none of them, and no e2e group
# selects this folder. Each install writes to the user's home folder, installs a
# tool globally or needs Claude Code, Codex, Antigravity or the GitHub CLI
# signed in, which the e2e job does not have. The plugin manifests, which these
# commands install, are checked by tests/test_plugin.py and by the plugin job.

# --8<-- [start:install]
uv tool install "odctl[mcp]"
# or, if you installed odctl with pipx
pipx install --force "odctl[mcp]"
# --8<-- [end:install]

# --8<-- [start:claude-code]
claude plugin marketplace add jaehyeon-kim/odctl
claude plugin install odctl@odctl
# --8<-- [end:claude-code]

# --8<-- [start:codex]
codex plugin marketplace add jaehyeon-kim/odctl
codex plugin add odctl@odctl
# --8<-- [end:codex]

# --8<-- [start:antigravity]
agy plugin install https://github.com/jaehyeon-kim/odctl
# --8<-- [end:antigravity]

# --8<-- [start:copy]
# The source of the installed release, which holds the skill
version=$(odctl info --json | python3 -c 'import json, sys; print(json.load(sys.stdin)["cli_version"])')
src=$(mktemp -d)
git clone --depth 1 --branch "v$version" https://github.com/jaehyeon-kim/odctl "$src" &&
  mkdir -p ~/.claude/skills &&
  rm -rf ~/.claude/skills/odctl &&
  cp -R "$src/skills/odctl" ~/.claude/skills/odctl
rm -rf "$src"
# --8<-- [end:copy]

# --8<-- [start:gh-skill]
# The release that is installed
version=$(odctl info --json | python3 -c 'import json, sys; print(json.load(sys.stdin)["cli_version"])')
gh skill install jaehyeon-kim/odctl odctl --pin "v$version" --agent claude-code --scope user
# --8<-- [end:gh-skill]

# --8<-- [start:check-copy]
ls ~/.claude/skills/odctl/SKILL.md
# --8<-- [end:check-copy]
