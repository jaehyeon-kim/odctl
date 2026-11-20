---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

Every night this script restarts odctl's PostgreSQL to drop idle connections, then applies the files in `migrations/`:

```bash
#!/usr/bin/env bash
odctl restart postgres
for f in migrations/*.sql; do
  docker exec -i postgres psql -U user -d odctl < "$f"
done
```

About one night in five the first file fails with a connection error, and the job still reports success. Rewrite the script so that neither happens again.

Write these files in the current folder, and no others:

- nightly.sh: the rewritten script.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
