---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

Our application keeps user sessions in the Valkey of my odctl workspace, and each session key expires after 30 minutes. Write a check I run from my laptop that exits 0 when the key `session:42` exists and expires within the next 30 minutes, and exits 1 in every other case. I have the Python package `valkey` installed.

Write these files in the current folder, and no others:

- check_session.py: the check.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
