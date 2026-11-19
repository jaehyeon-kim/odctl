---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace runs `ch-lite`, `kafka-lite` and `postgres`. The ClickHouse tables from old experiments take a lot of disk. Remove ClickHouse and everything it stored, so that the disk space comes back. Kafka and PostgreSQL keep running with their data.

Write these files in the current folder, and no others:

- cleanup.sh: the commands, in order, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
