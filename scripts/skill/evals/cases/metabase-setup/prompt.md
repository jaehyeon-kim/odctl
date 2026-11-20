---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill.

Write the script, run from my laptop, that prepares odctl's Metabase for our team: it creates the first admin account, `admin@example.com` with the password in the environment variable `MB_ADMIN_PASSWORD`, and adds the database `odctl` on odctl's PostgreSQL to Metabase under the name `odctl warehouse`. We run the script in every new environment, and someone may run it again on the same stack. Metabase uses a lot of memory, so we also stop it every evening and start it again in the morning; the dashboards the team builds must stay.

Write these files in the current folder, and no others:

- setup_metabase.sh: the setup script, as a bash script.
- stop.sh: the evening stop, as a bash script.
- start.sh: the morning start, as a bash script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
