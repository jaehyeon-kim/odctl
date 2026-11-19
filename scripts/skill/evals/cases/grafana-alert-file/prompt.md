---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

Add a Grafana alert to odctl's `telemetry` profile in my workspace that fires when Prometheus has not been able to scrape the MLflow tracking server for 2 minutes. The alert must still be there after `odctl restart telemetry`, and after `odctl down telemetry` followed by `odctl up telemetry`. Also write a check, run from my laptop, that Grafana has loaded the alert.

Write these files in the current folder, and no others:

- add_alert.sh: everything that adds the alert, as a bash script.
- check_alert.sh: the check, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
