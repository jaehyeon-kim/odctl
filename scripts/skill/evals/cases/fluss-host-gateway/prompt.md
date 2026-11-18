---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace has the `fluss` and `flink-lite` profiles. From my laptop, and only over HTTP, I want to create the Fluss table `demo.users` with the columns `id BIGINT`, its primary key, and `name STRING`, write three rows to it and print them. I have `requests` installed. Write the Python script, and a script that starts what it needs and runs it.

Write these files in the current folder, and no others:

- fluss_users.py: the Python script.
- run.sh: the script that starts what it needs and runs fluss_users.py.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
