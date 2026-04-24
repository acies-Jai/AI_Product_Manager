# Zepto PM Assistant

An agentic AI assistant for Product Managers at Zepto. Reads structured department documents, answers role-restricted questions via RAG, generates six PM artefacts, sends and reads email, and lets any team member propose knowledge-base updates through a chat interface.

---

## What you need before starting

### 1. Python 3.10 or later
Check with `python --version`.

### 2. Node.js 18 or later
Check with `node --version`. Required for the React frontend.

### 3. Groq API key (required)
The LLM runs on Groq (free tier available).
1. Sign up at [console.groq.com](https://console.groq.com)
2. Go to **API Keys** → **Create API Key**
3. Copy the key — you'll add it to `.env` in the next step

### 4. Gmail App Password (optional — needed for email features)
Without this, sent emails are logged to `outputs/email_log.txt` and inbox reading is unavailable.
1. Enable 2-Step Verification on your Google account
2. Go to **Google Account → Security → 2-Step Verification → App Passwords**
3. Select **Mail** → Generate
4. Save the 16-character password

---

## Setup

```bash
# 1. Clone
git clone https://github.com/acies-Jai/AI_Product_Manager.git
cd AI_Product_Manager

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
```

Open `.env` and fill in your values:
```
GROQ_API_KEY=gsk_...                     # required
GMAIL_SENDER=you@gmail.com               # optional
GMAIL_APP_PASSWORD=abcdabcdabcdabcd      # optional (no spaces)
```

---

## Running the app

Two terminals are required — the FastAPI backend and the React frontend.

**Terminal 1 — Backend:**
```bash
python -m uvicorn server:app --port 8502
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install   # first time only
npm run dev
```

Opens at **http://localhost:5173**

---

## First-run workflow

**Step 1 — Index documents**
Click **Index Documents** in the sidebar. Wait for the chunk count badge to update (~150 chunks).
This must be done before chat or artifact generation will work.

**Step 2 — Generate artefacts**
Click **⚡ Generate Artifacts**. After ~20–30 seconds, six tabs appear:
Roadmap · Key Focus Areas · Requirements · Success Metrics · Impact Quadrant · RICE Score.

**Step 3 — Chat**
Select a role from the dropdown and start asking questions. Try different roles to see
access control in action — Finance data is only visible to PM, Finance, and Leadership roles.

**Step 4 — Notify team (optional)**
Click **📧 Notify Team** in the sidebar to email the generated artefacts to all stakeholders
configured in `config/email_config.yaml`. This is a separate action from generation — it only
sends when you choose to.

---

## Demo scenarios

| Scenario | Role | Message |
|----------|------|---------|
| Full data access | Product Manager | "What is the H1 FY26 budget allocation?" |
| Access denied | Design | "What is the H1 FY26 budget allocation?" |
| Engineering context | Tech / Engineering | "What are the current sprint constraints?" |
| Send email via chat | Product Manager | "Send an email to Anirudh about the roadmap review" |
| Read inbox | Product Manager | "Check my inbox for recent emails" |
| Update a document | Product Manager | "Read tech.md and update the Feasibility Notes section to add that 2 engineers are joining next sprint" |
| Multi-turn memory | Product Manager | Ask about complaints, then "Based on that, what should we prioritise?" |

---

## Testing without the frontend

Start the FastAPI backend then run through the core scenarios with curl:

```bash
# 1. Check the server is up
curl http://localhost:8502/health

# 2. Index documents
curl -s -X POST http://localhost:8502/index | python -m json.tool

# 3. Chat as Product Manager (full access)
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the H1 FY26 budget allocation?","role":"Product Manager"}' \
  | python -m json.tool

# 4. Chat as Design (restricted — should be denied budget data)
curl -s -X POST http://localhost:8502/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the H1 FY26 budget allocation?","role":"Design"}' \
  | python -m json.tool

# 5. Generate all six PM artefacts
curl -s -X POST http://localhost:8502/generate-artifacts | python -m json.tool

# 6. Notify team by email
curl -s -X POST http://localhost:8502/notify-team | python -m json.tool

# 7. List indexed files
curl http://localhost:8502/files
```

For the full command reference — multi-turn conversations, document update with confirm/cancel, inbox, and SSE streaming — see [`system_guide/12_api_testing_guide.md`](system_guide/12_api_testing_guide.md).

**Endpoints at a glance:**

| Method | Path | What it does |
|--------|------|-------------|
| `GET`  | `/health` | Server status + chunk count |
| `GET`  | `/files` | File list + indexed status |
| `POST` | `/index` | Re-index all `inputs/` documents |
| `POST` | `/chat` | Synchronous chat — returns full reply + tool events |
| `POST` | `/chat/stream` | SSE streaming — yields one JSON event per graph node |
| `POST` | `/confirm` | Confirm or cancel a pending file write |
| `POST` | `/generate-artifacts` | Generate and save all six artefacts |
| `POST` | `/notify-team` | Email saved artefacts to stakeholders |
| `GET`  | `/artifacts` | Retrieve saved artefact content |

---

## Access control

Documents are tagged with one of three classification levels. Each role can only query levels it is permitted to see.

| Level | Documents | Who can see it |
|-------|-----------|---------------|
| `open` | product_context, employees | Everyone |
| `internal` | tech, sales, customer_support | All staff roles |
| `restricted` | finance | Product Manager, Finance, Leadership only |

Roles and their permissions are defined in `config/access_config.yaml`.

---

## Project layout

```
inputs/          # Department knowledge files (edit to customise context)
outputs/         # Generated artefacts (*.md)
config/          # access_config.yaml (RBAC) · email_config.yaml (recipients)
core/            # graph.py · tools.py · artifacts.py · email_service.py · files.py
frontend/        # React 18 + TypeScript + Vite frontend
system_guide/    # 12-file technical guide covering every system component
server.py        # FastAPI server (primary entry point)
rag.py           # Vector store + RBAC filtering
app.py           # Streamlit UI (fallback — not in requirements.txt)
```

---

## Adding your own data

1. Drop a `.md` file with `## ` headed sections into `inputs/`
2. Add it to `config/access_config.yaml` with a classification level (`open`, `internal`, or `restricted`)
3. Add relevant people to `inputs/employees.md` with their email addresses
4. Click **Index Documents** in the sidebar to re-index

---

## Known limitations

- No persistent memory across server restarts (MemorySaver is in-memory)
- One staged file change at a time per conversation turn
- No web search — agent searches internal documents only
- Artifact queries are hardcoded in `core/artifacts.py`
- No automated test suite — all testing is manual

---

## Further reading

See `system_guide/` for in-depth documentation on every component.
`system_guide/12_api_testing_guide.md` has complete curl commands for every endpoint.
