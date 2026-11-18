---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill.

Our CI runs `odctl up catalog` and then our tests, which create Iceberg tables through the REST catalog. Write a smoke check that runs on the CI host straight after `odctl up catalog` and before the tests. It must exit non-zero whenever the tests could not create a table, so that a broken stack is reported by the smoke check rather than by twenty failing tests. A failed job is often re-run on the same machine without a teardown.

Write these files in the current folder, and no others:

- smoke_catalog.sh: the smoke check, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
