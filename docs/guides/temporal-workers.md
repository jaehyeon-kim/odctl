# Temporal workers

The `temporal` profile runs the Temporal development server: the server, the Web UI and a SQLite database in one container. odctl runs only the server. Your own process runs the worker that executes workflows and activities. The code below comes from the end-to-end tests.

```bash
odctl up temporal
pip install temporalio==1.34.0
```

The gRPC endpoint is `127.0.0.1:7233` with the namespace `default`, and the Web UI is at `http://127.0.0.1:8233`.

## A worker and a workflow

The activity fails on its first attempt, so the result shows that the retry policy ran it again.

```python
import asyncio
from datetime import timedelta
from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.worker import Worker


@activity.defn
async def greet(name: str) -> str:
    if activity.info().attempt < 2:
        raise RuntimeError("first attempt fails on purpose")
    return f"hello {name}"


@workflow.defn
class Greet:
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            greet, name,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=3),
        )


async def main() -> None:
    client = await Client.connect("127.0.0.1:7233")
    async with Worker(client, task_queue="demo", workflows=[Greet], activities=[greet]):
        print(await client.execute_workflow(Greet.run, "odctl", id="greet-1", task_queue="demo"))


# The workflow sandbox imports this file again, so run main only as a script.
if __name__ == "__main__":
    asyncio.run(main())
```

## Wait for an approval

A workflow can wait for a signal, for example a person approving an agent's action. The workflow below waits until its `approve` signal arrives, and then returns who approved it:

```python
@workflow.defn
class Approval:
    def __init__(self) -> None:
        self.approver = None

    @workflow.signal
    def approve(self, approver: str) -> None:
        self.approver = approver

    @workflow.run
    async def run(self) -> str:
        await workflow.wait_condition(lambda: self.approver is not None)
        return f"approved by {self.approver}"
```

In `main` above, register it with the worker, start it, then send the signal:

```python
async with Worker(client, task_queue="demo", workflows=[Greet, Approval], activities=[greet]):
    handle = await client.start_workflow(Approval.run, id="approval-1", task_queue="demo")
    await handle.signal(Approval.approve, "alice")
    print(await handle.result())
```

Until the signal arrives, the Web UI lists the workflow as running.

## History

Workflow history is in the database file inside the container. It survives `odctl restart temporal`, and the tests check that a workflow left waiting for its signal resumes and completes afterwards. `odctl down` removes the history, as it removes every odctl service's data.
