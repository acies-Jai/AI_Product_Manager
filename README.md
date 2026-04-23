# Zepto PM Assistant

An agentic AI assistant for Product Managers. Reads structured department documents, answers
role-restricted questions via RAG, generates six PM artefacts, sends email notifications, and
lets any team member propose knowledge-base updates through a chat interface.

---

## What you need before starting

### 1. Python 3.10 or later
Check with `python --version`. Python 3.10+ is required for the union type syntax used in the code.

### 2. Groq API key (required)
The LLM runs on Groq (free tier available).
1. Sign up at [console.groq.com](https://console.groq.com)
2. Go to **API Keys** → **Create API Key**
3. Copy the key — you'll add it to `.env` in the next step

### 3. Gmail App Password (optional — needed for email features)
Without this, emails are logged to `outputs/email_log.txt` instead of being sent. Everything else works fine.
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

# 2. Create and activate a virtual environment (recommended)
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure credentials
cp .env.example .env
```

Open `.env` and fill in your values:
```
GROQ_API_KEY=gsk_...          # required
GMAIL_SENDER=you@gmail.com    # optional
GMAIL_APP_PASSWORD=abcdabcdabcdabcd  # optional (no spaces)
```

---

## Running the app

Two terminals needed — the FastAPI backend and the React frontend.

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

> The Streamlit app (`streamlit run app.py`) still works as a fallback but is no longer the primary UI. `streamlit` is not in `requirements.txt` — install it separately if needed.

---

## First-run workflow (do these in order)

**Step 1 — Index documents**
Click **🔍 Index Documents** in the sidebar. Wait for the caption to show `~150 chunks indexed`.
This must be done before the chat or artifact generation will work.

**Step 2 — Generate artefacts**
Click **⚡ Generate Artifacts**. After ~15–20 seconds, six tabs appear:
Roadmap · Key Focus Areas · Requirements · Success Metrics · Impact Quadrant · RICE Score.
If Gmail is configured, a branded HTML email is sent to all team members listed in
`config/email_config.yaml`.

**Step 3 — Chat**
Select a role from the dropdown and start asking questions. Try different roles to see
access control in action — Finance data is only visible to PM, Finance, and Leadership roles.

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

## Testing without the frontend (API server)

You can verify the entire system — RAG, chat, RBAC, document updates, artifact generation — without opening a browser. Start the FastAPI backend:

```bash
python -m uvicorn server:app --port 8502
```

Then run through the core scenarios with curl:

```bash
# 1. Check the server is up and documents are indexed
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
```

For the full command reference — multi-turn conversations, document update with confirm/cancel, inbox, and expected outputs — see [`system_guide/12_api_testing_guide.md`](system_guide/12_api_testing_guide.md).

**Endpoints at a glance:**

| Method | Path | What it does |
|--------|------|-------------|
| `GET`  | `/health` | Server status + chunk count |
| `POST` | `/index` | Re-index all `inputs/` documents |
| `POST` | `/chat` | Send a message; returns reply + tool events |
| `POST` | `/confirm` | Confirm or cancel a pending file write |
| `POST` | `/generate-artifacts` | Generate and save all six artefacts |
| `GET`  | `/artifacts` | Retrieve the saved artefacts |

---

## Project layout

```
inputs/          # Department knowledge files (edit these to customise context)
outputs/         # Generated artefacts (*.md) — committed to repo
config/          # access_config.yaml (RBAC) and email_config.yaml (recipients)
core/            # Agent logic: graph.py, tools.py, artifacts.py, email_service.py
system_guide/    # 11-file technical guide covering every system component
app.py           # Streamlit UI entry point
server.py        # FastAPI server for programmatic access
rag.py           # Vector store + RBAC filtering
```

---

## Adding your own data

1. Drop a `.md` file with `## ` headed sections into `inputs/`
2. Add it to `config/access_config.yaml` with a classification level (`open`, `internal`, or `restricted`)
3. Add relevant people to `inputs/employees.md` with their email addresses
4. Click ↺ **Reload Files** then 🔍 **Index Documents** in the sidebar

For a deeper understanding of how everything works, read `system_guide/README.md`.
