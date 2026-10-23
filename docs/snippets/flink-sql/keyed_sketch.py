# Sketch from docs/guides/flink-sql.md. It is not run by the end-to-end tests.

# --8<-- [start:keyed-sketch]
from pyflink.common import Types
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
from pyflink.datastream.state import ListStateDescriptor

WINDOWS_MS = {"10m": 600_000, "1h": 3_600_000, "1d": 86_400_000, "7d": 604_800_000}


class RollingSums(KeyedProcessFunction):
    def open(self, runtime_context: RuntimeContext):
        # Every event of the longest window, for each key, kept in Flink state.
        self.events = runtime_context.get_list_state(
            ListStateDescriptor("events", Types.TUPLE([Types.LONG(), Types.DOUBLE()]))
        )

    def process_element(self, value, ctx):
        now = ctx.timestamp()
        kept = [(t, a) for t, a in self.events.get() if now - t <= WINDOWS_MS["7d"]]
        kept.append((now, value[1]))
        self.events.update(kept)
        yield value[0], {n: sum(a for t, a in kept if now - t <= ms) for n, ms in WINDOWS_MS.items()}
# --8<-- [end:keyed-sketch]
