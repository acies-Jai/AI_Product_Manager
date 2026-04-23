# 12 — API Testing Guide
### Verify every system feature without touching the Streamlit UI

All commands use `curl`. Run them in any terminal after starting the server.

---

## Starting the server

```bash
python -m uvicorn server:app --port 8502
```

Leave this terminal open. Open a second terminal for the curl commands below.

The server auto-indexes documents on startup. If `inputs/` is empty it starts with 0 chunks — you can still call `/index` after adding files.

---

## 1. Health check

```bash
curl http://localhost:8502/health
```

Expected:
```json
{"status": "ok", "chunks_indexed": 152}
```

`chunks_indexed: 0` means documents are not indexed yet — run step 2.

---

## 1b. List input files

```bash
curl -s http://localhost:8502/files | python -m json.tool
```

Expected:
```json
{
    "files": ["tech", "finance", "sales", "design", "employees", "product_context", "customer_support"],
    "indexed": true,
    "chunks": 152
}
```

Useful to confirm which documents are loaded before indexing or chatting.

`chunks_indexed: 0` means documents are not indexed yet — run step 2.

---

## 2. Index documents

```bash
curl -s -X POST http://localhost:8502/index | python -m json.tool
```

Expected:
```json
{
    "chunks": 152,
    "files": ["tech", "finance", "sales", "design", "employees"]
}
```

Re-run this any time you edit a file in `inputs/` and want the changes picked up.

---

## 3. Chat — basic query

```bash
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the current sprint constraints?", "role": "Tech/Engineering"}' \
  | python -m json.tool
```

The response includes a `thread_id` — save it to continue the conversation in step 4.

Key fields in the response:
```json
{
    "thread_id": "abc-123-...",
    "intent": "search_query",
    "reply": "The current sprint has ...",
    "tool_events": [
        {
            "type": "search",
            "detail": "sprint constraints",
            "result_preview": "[tech / Sprint Planning]\n..."
        }
    ],
    "pending_write": null
}
```

---

## 4. Multi-turn conversation (memory across turns)

Pass the same `thread_id` on follow-up messages:

```bash
# Turn 1
THREAD=$(curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top user complaints?", "role": "Product Manager"}' \
  | python -m json.tool | grep thread_id | cut -d'"' -f4)

echo "Thread: $THREAD"

# Turn 2 — references turn 1 implicitly
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Based on that, what should we prioritise?\", \"role\": \"Product Manager\", \"thread_id\": \"$THREAD\"}" \
  | python -m json.tool
```

The agent has memory of turn 1 and answers turn 2 in context.

---

## 5. RBAC — access control verification

### Full access (PM sees restricted finance data)
```bash
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the H1 FY26 budget allocation?", "role": "Product Manager"}' \
  | python -m json.tool
```
Expected: actual budget figures in the reply.

### Access denied (Design role cannot see finance data)
```bash
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the H1 FY26 budget allocation?", "role": "Design"}' \
  | python -m json.tool
```
Expected: reply states the information is not available for this role. `tool_events` will show a search was attempted but returned no results.

### Other roles to test
| Role | Can see finance? | Can see tech/design? |
|------|-----------------|---------------------|
| `Product Manager` | Yes | Yes |
| `Finance` | Yes | Yes |
| `Leadership` | Yes | Yes |
| `Tech/Engineering` | No | Yes |
| `Design` | No | Yes |
| `Marketing` | No | Yes |

---

## 6. Document update flow (propose → confirm)

This is a two-step operation: the agent stages the change and waits for explicit confirmation.

### Step 1 — propose an update
```bash
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Read tech.md and update the Feasibility Notes section to say that 3 engineers are joining next sprint", "role": "Product Manager"}' \
  | python -m json.tool
```

Expected response has `pending_write` populated:
```json
{
    "thread_id": "abc-123-...",
    "pending_write": {
        "tool": "propose_update_section",
        "args": {
            "filename": "tech",
            "heading": "Feasibility Notes",
            "new_content": "3 engineers are joining next sprint..."
        }
    }
}
```

Copy the `thread_id`.

### Step 2a — confirm the write
```bash
curl -s -X POST http://localhost:8502/confirm \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "abc-123-...", "confirmed": true}' \
  | python -m json.tool
```

Expected:
```json
{"reply": "Done. The Feasibility Notes section in tech.md has been updated."}
```

Verify the file was actually changed:
```bash
# Windows PowerShell
Select-String -Path inputs/tech.md -Pattern "Feasibility Notes" -Context 0,5

# Or read the section directly
curl http://localhost:8502/chat -s -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "Read tech.md", "role": "Product Manager"}' \
  | python -m json.tool
```

### Step 2b — cancel the write
```bash
curl -s -X POST http://localhost:8502/confirm \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "abc-123-...", "confirmed": false}' \
  | python -m json.tool
```

Expected: acknowledgement that the change was discarded. The file is unchanged.

---

## 7. Send email via chat

```bash
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Send an email to Anirudh about the upcoming roadmap review", "role": "Product Manager"}' \
  | python -m json.tool
```

Expected: `tool_events` contains an entry with `"type": "email"` and the recipient address. If Gmail is not configured, check `outputs/email_log.txt` to confirm the email was logged.

---

## 8. Read inbox

```bash
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Check my inbox for recent emails", "role": "Product Manager"}' \
  | python -m json.tool
```

Expected: `tool_events` contains `"type": "inbox"` and the reply lists recent messages. Requires `GMAIL_SENDER` and `GMAIL_APP_PASSWORD` in `.env`.

---

## 9. Generate artefacts

```bash
# Generate only (no email)
curl -s -X POST http://localhost:8502/generate-artifacts | python -m json.tool

# Generate and email in one call
curl -s -X POST "http://localhost:8502/generate-artifacts?notify=true" | python -m json.tool
```

Takes 15–20 seconds. Expected response includes previews of all seven artefacts (first 300 chars each) and an `email_status` field (`"skipped"` by default, `"sent"` if `notify=true`):
```json
{
    "artifacts": {
        "roadmap": "| Now | Next | Later |\n...",
        "key_focus_areas": "1. **Reduce checkout abandonment**...",
        "requirements": "## Requirements\n...",
        "success_metrics": "| Initiative | Pre-launch...",
        "impact_quadrant": "--QUICK_WINS--\n...",
        "rice_score": "| Initiative | Reach | Impact...",
        "roadmap_timeline": "| Initiative | Start | End | Phase |..."
    },
    "email_status": "skipped"
}
```

Returns `400` if documents are not indexed — call `/index` first.

---

## 9b. Notify team separately

Sends the artifact email without regenerating. Use after reviewing the generated artefacts.

```bash
curl -s -X POST http://localhost:8502/notify-team | python -m json.tool
```

Returns `400` if no saved artefacts exist — generate them first.

---

## 10. Retrieve saved artefacts

```bash
curl -s http://localhost:8502/artifacts | python -m json.tool
```

Returns the full content of all artefact files from `outputs/`. Empty `{}` if artefacts have never been generated.

---

## 11. Streaming chat (SSE)

`POST /chat/stream` returns a [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) stream — one JSON event per graph node as it completes. This is the endpoint a custom frontend (React/Vite) should use to show the live thinking display.

```bash
curl -s -N -X POST http://localhost:8502/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the sprint constraints?", "role": "Tech/Engineering"}'
```

Each line looks like:
```
data: {"node": "classify_intent", "updates": {"intent": "search_query"}, "thread_id": "abc-123"}
data: {"node": "retrieve_context", "updates": {"retrieved_context": [...]}, "thread_id": "abc-123"}
data: {"node": "generate_response", "updates": {"reply": "...", "tool_events": [...]}, "thread_id": "abc-123"}
data: {"node": "__done__", "thread_id": "abc-123"}
```

The `thread_id` is auto-generated if not supplied. Pass it back in subsequent requests to continue the conversation.

**JavaScript fetch example:**
```js
const res = await fetch("http://localhost:8502/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ message, role, thread_id }),
});
const reader = res.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const lines = decoder.decode(value).split("\n");
  for (const line of lines) {
    if (line.startsWith("data: ")) {
      const event = JSON.parse(line.slice(6));
      if (event.node === "__done__") break;
      // handle event.node + event.updates
    }
  }
}
```

---

## Quick smoke test — run all steps in order

```bash
# 1. Health
curl -s http://localhost:8502/health

# 2. Index
curl -s -X POST http://localhost:8502/index | python -m json.tool

# 3. PM chat
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the H1 FY26 budget allocation?","role":"Product Manager"}' \
  | python -m json.tool

# 4. RBAC denial
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the H1 FY26 budget allocation?","role":"Design"}' \
  | python -m json.tool

# 5. Generate artefacts (no email)
curl -s -X POST http://localhost:8502/generate-artifacts | python -m json.tool

# 5b. Generate artefacts AND notify team in one call
curl -s -X POST "http://localhost:8502/generate-artifacts?notify=true" | python -m json.tool

# 6. Fetch saved artefacts
curl -s http://localhost:8502/artifacts | python -m json.tool

# 7. Notify team separately (uses already-saved artefacts)
curl -s -X POST http://localhost:8502/notify-team | python -m json.tool
```

All six commands should complete without errors and produce non-empty JSON.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Connection refused` | Server not running | `python -m uvicorn server:app --port 8502` |
| `chunks_indexed: 0` | Documents not indexed | `POST /index` |
| `400 Index documents first` | `/generate-artifacts` before index | Run `/index` first |
| `reply` is empty string | Graph produced no output node | Check terminal running the server for traceback |
| Finance data returned for Design role | RBAC misconfigured | Check `config/access_config.yaml` classification levels |
| `pending_write` never populated | Model wrote tool call as plain text | Rephrase: "Read tech.md and update the X section to say Y" |
