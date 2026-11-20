---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

`odctl up postgres` fails on my laptop because my own PostgreSQL already listens on port 5432, and I cannot stop it. Run odctl's PostgreSQL on port 5433 instead, and tell me the connection URL my application on the laptop should use. The Iceberg catalog and other odctl profiles I start later must keep working with it.

Write these files in the current folder, and no others:

- start_pg.sh: the commands, in order, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
