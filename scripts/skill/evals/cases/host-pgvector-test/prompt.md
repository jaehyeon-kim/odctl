---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

Write a pytest test that runs on my laptop, not in a container, and shows that odctl's PostgreSQL can find the nearest vector with pgvector. Also write the script that starts what the test needs, creates the Python environment for it and runs it. I run the script many times a day on the same stack, and my laptop's `python3` is whatever Homebrew last installed.

Write these files in the current folder, and no others:

- test_vector.py: the test.
- run_test.sh: the script that starts what the test needs, creates the Python environment and runs the test.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
