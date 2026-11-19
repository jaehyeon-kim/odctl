---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

Write a Python script that loads `orders.csv` (columns `order_id`, `customer`, `amount`) into the table `dev.orders` in the `odctl` database of odctl's PostgreSQL, and the command that runs it in a container, not on my laptop. A scheduler runs it every night, and each night `orders.csv` is a full export of all orders.

Write these files in the current folder, and no others:

- load_orders.py: the loader.
- run_load.sh: the script that runs the loader in a container.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
