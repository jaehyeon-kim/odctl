# Python steps of the Label Studio guide. Each section is copied into the guide page.

# --8<-- [start:load]
import json
import subprocess


def quote(text):
    """Quote a value as an SQL string literal."""
    return "'" + text.replace("'", "''") + "'"


statements = [
    "SET client_min_messages = warning;",
    """CREATE TABLE IF NOT EXISTS dev.labels (
        sample_id  text NOT NULL,
        label      text NOT NULL,
        source     text NOT NULL,
        arrived_at timestamptz NOT NULL DEFAULT now(),
        PRIMARY KEY (sample_id, source)
    );""",
]
with open("annotations.json") as file:
    tasks = json.load(file)
for task in tasks:
    # A task skipped in the UI has an annotation with no result. A task with
    # more than one annotation keeps its latest.
    done = [a for a in task["annotations"] if not a["was_cancelled"] and a["result"]]
    if not done:
        continue
    latest = max(done, key=lambda annotation: annotation["updated_at"])
    label = latest["result"][0]["value"]["choices"][0]
    statements.append(
        "INSERT INTO dev.labels (sample_id, label, source)"
        f" VALUES ({quote(task['data']['sample_id'])}, {quote(label)}, 'label-studio')"
        " ON CONFLICT (sample_id, source) DO UPDATE"
        " SET label = EXCLUDED.label, arrived_at = now()"
        " WHERE labels.label <> EXCLUDED.label;"
    )
subprocess.run(
    ["docker", "exec", "-i", "postgres", "psql", "-q", "-v", "ON_ERROR_STOP=1", "-U", "user", "-d", "odctl"],
    input="\n".join(statements),
    text=True,
    check=True,
)
# --8<-- [end:load]
