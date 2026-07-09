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

1. What profiles were you trying to launch? (e.g., `dml up airflow spark ckh1`)
2. Run this CLI command: '...'
3. See error

**Expected behavior**

A clear and concise description of what you expected to happen.

**Traceback / Error Logs**

If applicable, paste the full CLI error or the specific container logs here (you can fetch container logs using `dml logs <profile> -s <service>`):

```text
# Paste logs here


```

**Environment (please complete the following information):**

* OS: [e.g. Ubuntu 24.04, macOS Sonoma, Windows 11 / WSL2]
* Python Version: [e.g. 3.12]
* `dml-cli` Version: [e.g. 0.0.3]
* Docker Version: [e.g. Docker Desktop 4.28.0, Docker Engine 25.0]

## **Additional context**

* Did you customize any files in your local `./.dml/` workspace? (e.g., changing ports in `compose-orch.yml` or editing `registry.yml`)
* How much RAM/CPU is allocated to your Docker daemon? (Many Open Data profiles are resource-heavy)
* Add any other context about the problem here.
