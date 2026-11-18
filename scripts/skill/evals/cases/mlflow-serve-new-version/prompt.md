---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

odctl's model server serves `models:/churn-model@champion` in my workspace. Our scoring service runs in its own container on odctl's Docker network and calls that server. After each retrain, a job in another container on the same network registers the model of the training run, whose id it gets in the environment variable `RUN_ID` (artifact path `model`), as a new version of `churn-model` and moves the alias `champion` to it. From then on the scoring service must get its predictions from the new version, and it must not fail while the server changes over.

Write these files in the current folder, and no others:

- register_version.py: the job's code that registers the new version and moves the alias.
- reload.sh: the commands, run on my laptop, that make the model server serve the new version, as a bash script.
- score_client.py: the scoring service's function that sends rows to the model server and returns the predictions.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
