---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill.

Our agent application sends the OpenTelemetry metric `gen_ai.client.token.usage` to odctl's telemetry collector, with the OpenTelemetry SDK's default settings. Write a Python script that runs in a container on odctl's Docker network and prints how many tokens the model calls used in the last hour, in total. The total must include an application that started 10 minutes ago, and one that sent its metrics once and then stopped.

Write these files in the current folder, and no others:

- token_usage.py: the script.
- run.sh: the commands that run the script in a container on odctl's network, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
