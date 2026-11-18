---
tags: [odctl]
max_turns: 80
timeout_seconds: 1500
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

You work in the current folder. odctl is installed in py/; run it as py/bin/odctl, and do not install anything else. Docker is not available on this machine, so odctl commands that need Docker fail here: write the files the request asks for, and do not try to start containers. Use the odctl skill. The current folder holds the user's odctl workspace, `.odctl/`.

My odctl workspace has the `fluss` and `flink-lite` profiles. Keep the latest price of each product in the Fluss table `shop.latest_price`, with `product_id` as its primary key, using Flink SQL. Load these price updates, which arrived in this order: product 1 at 10.00, product 2 at 20.00, product 1 at 12.50, product 3 at 7.00, product 2 at 19.00. Then check that the table holds exactly one row for each product, with its last price, and exit 1 when it does not.

Write these files in the current folder, and no others:

- latest_price.sql: the Flink SQL that creates the table and loads the updates.
- run.sh: the script that starts what is needed, runs latest_price.sql and runs the check.
- reply.md: your final reply to the person who asked: what you wrote, what each file does and anything they must know before they run it. The reply is the last thing you write.
