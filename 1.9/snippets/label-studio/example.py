"""Labels two samples in Label Studio and loads the labels into PostgreSQL.

It creates a project, imports two tasks, labels them through the API, exports the
annotations and loads them into the label table, `dev.labels`, in the odctl database. Start the
profile with `odctl up label-studio` first, then run `python3 example.py`. It uses
only the Python standard library and `docker exec` for psql.
"""

import json
import subprocess
import urllib.request

URL = "http://127.0.0.1:8088"
TOKEN = "odctl-label-studio-token"
LABEL_CONFIG = (
    '<View><Text name="text" value="$text"/>'
    '<Choices name="label" toName="text">'
    '<Choice value="1"/><Choice value="0"/></Choices></View>'
)
# Each sample is a request to the driver model: its ID, a text that describes it,
# and the score a person gives it.
SAMPLES = [
    ("e-1", "Driver 1001, conv_rate 0.9", "1"),
    ("e-2", "Driver 1002, conv_rate 0.75", "0"),
]


def call(path, body=None):
    """Send one request to the Label Studio API and return its JSON answer."""
    request = urllib.request.Request(
        URL + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Authorization": f"Token {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def quote(text):
    """Quote a value as an SQL string literal."""
    return "'" + text.replace("'", "''") + "'"


project = call("/api/projects", {"title": "Example", "label_config": LABEL_CONFIG})
call(
    f"/api/projects/{project['id']}/import",
    [{"sample_id": sample_id, "text": text} for sample_id, text, _ in SAMPLES],
)
tasks = call(f"/api/tasks?project={project['id']}")["tasks"]
labels = {sample_id: label for sample_id, _, label in SAMPLES}
for task in tasks:
    # A person labels each task in the UI; this script stands in for them.
    choice = {"choices": [labels[task["data"]["sample_id"]]]}
    result = {"from_name": "label", "to_name": "text", "type": "choices", "value": choice}
    call(f"/api/tasks/{task['id']}/annotations", {"result": [result]})

statements = [
    "SET client_min_messages = warning;",
    "CREATE TABLE IF NOT EXISTS dev.labels (sample_id text NOT NULL, label text NOT NULL,"
    " source text NOT NULL, arrived_at timestamptz NOT NULL DEFAULT now(),"
    " PRIMARY KEY (sample_id, source));",
]
for task in call(f"/api/projects/{project['id']}/export?exportType=JSON"):
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
statements.append(
    "SELECT sample_id, label, source FROM dev.labels WHERE sample_id LIKE 'e-%' ORDER BY sample_id;"
)
subprocess.run(
    ["docker", "exec", "-i", "postgres", "psql", "-q", "-v", "ON_ERROR_STOP=1", "-U", "user", "-d", "odctl"],
    input="\n".join(statements),
    text=True,
    check=True,
)
