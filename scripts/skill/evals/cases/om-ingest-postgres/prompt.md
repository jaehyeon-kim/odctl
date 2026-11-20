---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill.

Catalogue the tables of the database `odctl` on odctl's PostgreSQL in OpenMetadata, through OpenMetadata's REST API from my laptop, and wait until the ingestion has finished. Our CI runs this on every build against the same long-lived stack.

Write these files in the current folder, and no others:

- catalogue_pg.sh: the script, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
