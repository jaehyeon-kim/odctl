---
name: Bug Report
about: Create a report to help us improve the Open Data Stack
title: "[BUG] "
labels: bug
assignees: ""
---

**Describe the bug**

A clear and concise description of what the bug is.

**To Reproduce**

Steps to reproduce the behavior:

1. What profiles were you trying to launch? (for example, `odctl up airflow spark-lite ch-lite`)
2. Run this CLI command: '...'
3. See error

**Expected behavior**

A clear and concise description of what you expected to happen.

**Traceback / Error Logs**

If applicable, paste the full CLI error or the specific container logs here (you can fetch container logs using `odctl logs <profile> -s <service>`):

```text
# Paste logs here


```

**Environment (please complete the following information):**

* OS: [for example Ubuntu 24.04, macOS Sonoma, Windows 11 / WSL2]
* Python Version: [for example 3.12]
* odctl version (`odctl info`): [for example 1.0.0]
* Docker Version: [for example Docker Desktop 4.28.0, Docker Engine 25.0]

## **Additional context**

* Did you customize any files in your local `./.odctl/` workspace? (for example, changing ports in `compose-orch.yml` or editing `registry.yml`)
* How much RAM/CPU is allocated to your Docker daemon? (Many Open Data profiles are resource-heavy)
* Add any other context about the problem here.
