📧 Email Productivity Agent

A full-stack email triage, drafting, and productivity assistant built with FastAPI + Streamlit + Local LLM (or mock fallback).

📄 Assignment Specification

This project was developed according to the specification in:
/mnt/data/Assignment - 2.pdf (local assignment file provided)

⭐ Overview

The Email Productivity Agent helps users efficiently handle email overload by:

✔ Loading a mock inbox of 20 emails
✔ Using editable Prompt Brain templates to process emails
✔ Automatically categorizing emails
✔ Extracting tasks and deadlines
✔ Generating draft replies using an AI agent
✔ Allowing users to save, edit, and manage drafts
✔ Providing a complete UI for inbox → agent → drafts workflow
✔ Running fully locally (no API keys required)

This prototype meets all assignment requirements, including custom prompts, agent queries, drafting system, backend + UI integration, and the final demo flow.

🚀 Features
📥 Inbox

Loads a mock inbox (data/mock_inbox.json)

Shows sender, subject, body, timestamp

“Process” button → categorize & extract tasks

Saves output in data/processed.json

🧠 Prompt Brain

Stored in /prompts/default_prompts.json

Fully editable in UI

Customizable prompts for:

Categorization

Task extraction

Draft reply generation

🤖 AI Agent

Triggered on any email for:

Summaries

Task extraction

Draft replies (tone-controlled)

Custom user instructions

Works via:
POST /agent/query

Uses local LLM (like distilgpt2) or mock LLM fallback.

✍️ Draft Management

Full CRUD support:

Action	API	UI
Create draft	POST /drafts	Composer or Agent reply
List drafts	GET /drafts	Drafts section
Get draft	GET /drafts/{id}	Auto-loaded when editing
Update draft	PUT /drafts/{id}	Inline editor
Delete draft	DELETE /drafts/{id}	Drafts section

All drafts stored in:
data/drafts.json

🖥️ UI (Streamlit)

Inbox viewer

Prompt editor

Agent panel

Draft editor

Composer for custom drafts

Processed output viewer

Assignment reference

Local backend configuration

📂 Project Structure
email-agent/
│
├── backend/
│   ├── app.py               # FastAPI server
│   ├── llm.py               # Local+mock LLM engine
│   └── __init__.py
│
├── ui/
│   └── app.py               # Streamlit UI
│
├── data/
│   ├── mock_inbox.json      # 20 mock emails
│   ├── processed.json       # Saved processed outputs
│   └── drafts.json          # Saved drafts
│
├── prompts/
│   └── default_prompts.json # Prompt Brain
│
└── README.md

🛠️ Installation & Setup
1. Clone the repo
git clone <your-repo-url>
cd email-agent

2. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

3. Install dependencies
pip install --upgrade pip
pip install fastapi uvicorn requests
pip install streamlit
pip install transformers accelerate sentencepiece
pip install --index-url https://download.pytorch.org/whl/cpu torch

4. Set environment variables (optional local LLM)

To use a small local model:

$env:LOCAL_LLM = "1"
$env:LOCAL_MODEL_NAME = "distilgpt2"


To use mock LLM only:

$env:LOCAL_LLM = "0"

▶️ Running the App
1. Start backend

Run from project root:

uvicorn backend.app:app --reload --port 8000


Server runs at: http://127.0.0.1:8000

2. Start UI

Open a second terminal:

streamlit run ui/app.py


UI opens at:
http://localhost:8501

🔌 API Endpoints
📬 Inbox
Method	Endpoint	Description
GET	/inbox	Returns 20 mock emails
⚙️ Prompts
Method	Endpoint
GET	/prompts
POST	/prompts
📨 Processing
Method	Endpoint
POST	/process/{id}
GET	/processed
🤖 Agent
Method	Endpoint	Body
POST	/agent/query	{ email_id, prompt_type, user_instruction? }
✍️ Drafts (Full CRUD)
Method	Endpoint
POST	/drafts
GET	/drafts
GET	/drafts/{id}
PUT	/drafts/{id}
DELETE	/drafts/{id}
🎮 How to Use (Demo Flow)

Start Backend + Start UI

In UI → set backend URL → click Load Inbox

Expand any email → click Process

View results in right panel (processed viewer)

Use Agent actions: Summarize / What tasks / Draft reply

Click Save agent reply as draft

Go to Drafts panel (right side)

Edit or delete drafts

Use Composer to write custom drafts

Download draft (optional) or use in demo

This mirrors the expected 6–10 minute final demonstration.

🧠 Architecture Overview
Backend (FastAPI)

Stateless JSON-file based storage

Prompt-based LLM interactions using agent_query()

Local LLM option via HuggingFace pipelines

Mock LLM fallback for stable behavior

Fully offline and self-contained

UI (Streamlit)

Expander-based inbox viewer

Prompt editing system

Agent button actions

Draft composer + editor

Responsive layout

Data Storage

Located inside /data/ for easy grading and inspection.
