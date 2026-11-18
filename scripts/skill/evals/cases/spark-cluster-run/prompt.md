---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace runs `spark-full`, with three workers. Run the PySpark job `count_words.py` in the current folder on those workers, not on a single machine. Write a script that starts what the job needs, waits until all three workers can take work, and runs the job, and a check I run from my laptop that exits 1 unless the job's last run used the cluster.

Write these files in the current folder, and no others:

- run.sh: the script that starts what the job needs, waits and runs the job.
- check_cluster.sh: the check, run from my laptop.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
