# Commands from docs/guides/mcp-server.md. .github/scripts/smoke.sh runs
# list-tools and list-tools-changes in the kafka-lite case, and starts the server
# that the .mcp.json of claude-code names. claude-code needs Claude Code, so
# smoke.sh does not run it.

# --8<-- [start:install]
uv tool install "odctl[mcp]"
# --8<-- [end:install]

# --8<-- [start:claude-code]
# Writes .mcp.json in this folder.
claude mcp add --scope project odctl -- odctl mcp
# --8<-- [end:claude-code]

# --8<-- [start:list-tools]
python mcp_client.py odctl mcp
# --8<-- [end:list-tools]

# --8<-- [start:list-tools-changes]
python mcp_client.py odctl mcp --allow-changes
# --8<-- [end:list-tools-changes]
