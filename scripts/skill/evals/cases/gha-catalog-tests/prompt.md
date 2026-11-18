---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill.

This folder is my repository. The tests in `tests/` call the Iceberg REST catalog of odctl's stack from the test process, and `requirements-test.txt` lists what they need. Write a GitHub Actions workflow that runs them on every pull request: it starts what the tests need with odctl, runs `pytest tests/`, and always tears down what it started, even when the tests fail.

Write these files in the current folder, and no others:

- integration.yml: the workflow, which I will put in `.github/workflows/`.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
