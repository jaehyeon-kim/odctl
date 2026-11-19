---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace runs `kafka-full`. Write a Python script I run on my laptop that creates the topic `payments` with 6 partitions, so that every partition has a copy on each of the three brokers and a write with `acks=all` fails when fewer than two copies are in sync. The script then writes 100 messages to it with `acks=all`, and exits 1 unless every partition of the topic has three in-sync replicas. I have `confluent-kafka` installed. Also write the script that starts what it needs and runs it.

Write these files in the current folder, and no others:

- payments.py: the Python script.
- run.sh: the script that starts what it needs and runs payments.py.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
