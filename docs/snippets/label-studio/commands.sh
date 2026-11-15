# Commands of the Label Studio guide. Each section is copied into the guide page.

# --8<-- [start:up]
odctl up label-studio
# --8<-- [end:up]

# --8<-- [start:project]
# A project that labels each request 1 or 0, the two scores the driver model
# gives. It prints the project ID. $text names each task's text field, which
# Label Studio fills in, so it stays in single quotes. The shellcheck line tells
# the repository's shell linter that this is intended.
TOKEN=odctl-label-studio-token
# shellcheck disable=SC2016
PROJECT_ID=$(curl -s -X POST http://127.0.0.1:8088/api/projects \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"title": "Driver requests", "label_config": "<View><Text name=\"text\" value=\"$text\"/><Choices name=\"label\" toName=\"text\"><Choice value=\"1\"/><Choice value=\"0\"/></Choices></View>"}' \
  | python3 -c "import json, sys; print(json.load(sys.stdin)['id'])")
echo "$PROJECT_ID"
# --8<-- [end:project]

# --8<-- [start:import]
# Two tasks, each a request's ID and a text that describes the request.
curl -s -X POST "http://127.0.0.1:8088/api/projects/$PROJECT_ID/import" \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '[{"sample_id": "r-1", "text": "Driver 1001, conv_rate 0.9"}, {"sample_id": "r-2", "text": "Driver 1002, conv_rate 0.75"}]'
echo
# --8<-- [end:import]

# --8<-- [start:read]
# This prints the sample ID and text of each task in the project.
curl -s "http://127.0.0.1:8088/api/tasks?project=$PROJECT_ID" -H "Authorization: Token $TOKEN" \
  | python3 -c "import json, sys; [print(t['data']['sample_id'], t['data']['text']) for t in json.load(sys.stdin)['tasks']]"
# --8<-- [end:read]

# --8<-- [start:annotate]
# Labels the first task 1 and the second 0 from a script, as a person does in
# the UI.
read -r FIRST SECOND < <(curl -s "http://127.0.0.1:8088/api/tasks?project=$PROJECT_ID" -H "Authorization: Token $TOKEN" \
  | python3 -c "import json, sys; print(*[t['id'] for t in json.load(sys.stdin)['tasks']])")
annotate() {
  curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://127.0.0.1:8088/api/tasks/$1/annotations" \
    -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
    -d "{\"result\": [{\"from_name\": \"label\", \"to_name\": \"text\", \"type\": \"choices\", \"value\": {\"choices\": [\"$2\"]}}]}"
}
annotate "$FIRST" 1
annotate "$SECOND" 0
# --8<-- [end:annotate]

# --8<-- [start:export]
# Exports the project's tasks with their annotations as JSON.
curl -s "http://127.0.0.1:8088/api/projects/$PROJECT_ID/export?exportType=JSON" \
  -H "Authorization: Token $TOKEN" -o annotations.json
# --8<-- [end:export]

# --8<-- [start:load]
python3 load.py
docker exec postgres psql -U user -d odctl -c "SELECT sample_id, label, source FROM dev.labels ORDER BY sample_id"
# --8<-- [end:load]

# --8<-- [start:container]
# Inside the odctl network, Label Studio is label-studio:8080. This prints the
# email of the user that the token belongs to.
docker run --rm --network odctl curlimages/curl:8.17.0 -s \
  -H "Authorization: Token odctl-label-studio-token" http://label-studio:8080/api/current-user/whoami \
  | python3 -c "import json, sys; print(json.load(sys.stdin)['email'])"
# --8<-- [end:container]
