---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace runs `kafka-full`. The Kafka topic `clicks` holds JSON messages such as `{"user_id": 7, "url": "/home", "ts": "2026-11-18 10:00:00"}`, and new ones arrive all the time. With Flink on the `flink-full` profile, copy every message of the topic, including the ones already in it, into the Iceberg table `web.clicks`, and keep copying new messages as they arrive. Then show with Trino that the rows are in the table.

Write these files in the current folder, and no others:

- clicks.sql: the Flink SQL.
- run.sh: the script that starts what is needed and starts the copy.
- check.sh: a check that runs a query in Trino and exits 1 unless the copied rows are in the table.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
