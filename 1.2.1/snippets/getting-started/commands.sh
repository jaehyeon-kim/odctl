# Commands from docs/getting-started.md. .github/scripts/smoke.sh runs list,
# list-details, explain, info, ps, ps-all, logs, logs-time, restart and
# down-dry-run in the kafka-lite case. The e2e workflow itself starts each
# profile with up and stops it with down and down-all.

# --8<-- [start:install]
uv tool install odctl
# or
pipx install odctl
# --8<-- [end:install]

# --8<-- [start:init]
odctl init
# --8<-- [end:init]

# --8<-- [start:list]
odctl list
# --8<-- [end:list]

# --8<-- [start:list-details]
odctl list -d
# --8<-- [end:list-details]

# --8<-- [start:explain]
odctl explain kafka-lite
# --8<-- [end:explain]

# --8<-- [start:dry-run]
odctl up kafka-lite --dry-run
# --8<-- [end:dry-run]

# --8<-- [start:up]
odctl up kafka-lite
# --8<-- [end:up]

# --8<-- [start:info]
odctl info
# --8<-- [end:info]

# --8<-- [start:ps]
odctl ps kafka-lite
# --8<-- [end:ps]

# --8<-- [start:ps-all]
odctl ps --all
# --8<-- [end:ps-all]

# --8<-- [start:logs]
odctl logs kafka-lite -s connect -n 3
# --8<-- [end:logs]

# --8<-- [start:logs-time]
odctl logs kafka-lite -s connect --since 10m --until 1s -t -n 2
# --8<-- [end:logs-time]

# --8<-- [start:restart]
odctl restart kafka-lite
# --8<-- [end:restart]

# --8<-- [start:down-dry-run]
odctl down kafka-lite --dry-run
# --8<-- [end:down-dry-run]

# --8<-- [start:down]
odctl down kafka-lite
# --8<-- [end:down]

# --8<-- [start:down-all]
odctl down --all --volumes
# --8<-- [end:down-all]

# --8<-- [start:down-all-yes]
odctl down --all --volumes --yes
# --8<-- [end:down-all-yes]
