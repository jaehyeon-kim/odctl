---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My MLflow run, whose id my scripts get in the environment variable `RUN_ID`, logged an XGBoost model at the artifact path `model` to odctl's MLflow. From my laptop, register that model as `churn-model` with the alias `champion`, have odctl's model server serve the `champion` version, and score the two rows `[[0.5, 1.2], [3.1, 0.4]]` against it.

Write these files in the current folder, and no others:

- register.py: the Python script that registers the model and sets the alias, run on my laptop.
- serve.sh: the commands that make the model server serve the model and score the two rows, in order, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
