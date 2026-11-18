---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace runs `ch-full`. Write a bash script I run on my laptop, with curl, that creates a ClickHouse table whose rows are spread over both shards, with two copies of each shard, loads the numbers 1 to 10000 into it, and exits 1 unless a query sees all 10000 rows.

Write these files in the current folder, and no others:

- load_and_check.sh: the script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
