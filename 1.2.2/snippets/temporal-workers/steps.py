# Python from docs/guides/temporal-workers.md. .github/scripts/smoke.sh runs the
# worker section as a script; example.py is the script with the approval steps.

# --8<-- [start:worker]
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
# --8<-- [end:worker]


# --8<-- [start:approval-workflow]
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
# --8<-- [end:approval-workflow]

# --8<-- [start:approval-run]
async def main() -> None:
    client = await Client.connect("127.0.0.1:7233")
    async with Worker(client, task_queue="demo", workflows=[Greet, Approval], activities=[greet]):
        print(await client.execute_workflow(Greet.run, "odctl", id="greet-1", task_queue="demo"))
        handle = await client.start_workflow(Approval.run, id="approval-1", task_queue="demo")
        await handle.signal(Approval.approve, "alice")
        print(await handle.result())
# --8<-- [end:approval-run]
