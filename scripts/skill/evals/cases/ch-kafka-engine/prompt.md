---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace runs `kafka-full` and `ch-full`. The Kafka topic `page_views` holds JSON messages such as `{"user_id": 7, "path": "/home"}`, and new ones keep arriving. Make ClickHouse read every message of the topic, including the ones already in it, into a table, with ClickHouse's own Kafka table engine and no other service. Then check that the rows arrived, and exit 1 when they did not.

Write these files in the current folder, and no others:

- page_views.sql: the ClickHouse SQL.
- run.sh: the script that applies page_views.sql and runs the check.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
