---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill.

Our nightly batch job `nightly_orders` runs on my laptop, outside Docker. It reads the dataset `raw.orders` and writes `mart.daily_orders`. Report each run of it to odctl's Marquez: the job calls a script when it starts, and again when it ends with its outcome, success or failure. Also write a script that prints the state of the job's latest run as Marquez has it.

Write these files in the current folder, and no others:

- report_run.sh: the script the job calls at its start and at its end, as a bash script.
- latest_run.sh: the script that prints the state of the latest run, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
