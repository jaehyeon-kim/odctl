---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

Write the setup script for our test suite on odctl's stack: it creates the Iceberg table `demo.driver_stats` with a few rows, applies the Feast repository in `feature_repo/`, uploads `dags/materialize_driver_stats.py` to Airflow and runs that DAG once. Every CI job runs the script on the same long-lived stack.

Write these files in the current folder, and no others:

- setup.sh: the setup script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
