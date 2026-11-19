---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

`DbCheck.java` here prints the version of a PostgreSQL server; it reads the JDBC URL, user and password from the environment variables `JDBC_URL`, `DB_USER` and `DB_PASSWORD`. Write a script that runs it in an `eclipse-temurin:21-jdk` container against odctl's PostgreSQL. Use the PostgreSQL JDBC driver that odctl already has; do not download a driver. Nothing of odctl's is running yet.

Write these files in the current folder, and no others:

- run_dbcheck.sh: the script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
