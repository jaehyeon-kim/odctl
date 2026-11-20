---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill.

I run odctl's stack on my laptop. Write a PySpark job that reads every message of the Kafka topic `orders` and prints them, and a script that starts what the job needs with odctl and runs the job in the stack's Spark container.

Write these files in the current folder, and no others:

- read_orders.py: the PySpark job.
- run.sh: the script that starts what the job needs and runs it.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
