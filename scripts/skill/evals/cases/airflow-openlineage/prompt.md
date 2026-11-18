---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

Airflow is running in my odctl workspace with our DAGs, and its run history must stay. Make Airflow send the lineage of every DAG run to odctl's Marquez from now on. Also write a check, run from my laptop, that exits 0 once Marquez has a job for the DAG `daily_sales` after its next run, and exits 1 otherwise.

Write these files in the current folder, and no others:

- enable_lineage.sh: the steps, in order, as a bash script.
- check_lineage.sh: the check, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
