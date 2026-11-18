---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace runs `spark-full`. The file `trips.csv` in the current folder holds taxi trips, with a header line. Put the file in the stack's object storage from my laptop, then load it with a PySpark job, run in the stack's Spark, into the Iceberg table `taxi.trips`. Also write a check I run from my laptop that exits 1 unless the table holds every trip in the file.

Write these files in the current folder, and no others:

- load_trips.py: the PySpark job.
- run.sh: the script that uploads the file and runs the job.
- check_trips.sh: the check, run from my laptop.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
