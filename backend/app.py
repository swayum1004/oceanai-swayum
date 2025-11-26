from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import json,uuid
import os
from datetime import datetime,timezone

from backend.llm import call_llm, agent_query as llm_agent_query

BASE = Path(__file__).resolve().parent.parent  

INBOX_PATH = BASE / "data" / "mock_inbox.json"
PROMPT_PATH = BASE / "prompts" / "default_p.json"
PROCESSED_PATH = BASE / "data" / "processed.json"
DRAFTS_PATH = BASE / "data" / "drafts.json"

app = FastAPI(title="Email Productivity Agent - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def load_json(path: Path):
    if path.exists():
        return json.loads(path.read_text())
    return None

def write_json_file(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2))

@app.get("/inbox")
def get_inbox():
    inbox = load_json(INBOX_PATH)
    return inbox or []

@app.post("/process/{email_id}")
def process_email(email_id: int):
    inbox = load_json(INBOX_PATH) or []
    email = next((e for e in inbox if e["id"] == email_id), None)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    prompts = load_json(PROMPT_PATH) or {}
    cat_prompt = prompts["categorization_prompt"].replace("{email_text}", email["body"])
    act_prompt = prompts["action_prompt"].replace("{email_text}", email["body"])

    cat_out = call_llm(cat_prompt)
    act_out = call_llm(act_prompt)

    processed = load_json(PROCESSED_PATH) or {}
    processed[str(email_id)] = {
        "email": email,
        "category_output": cat_out,
        "action_output": act_out
    }
    PROCESSED_PATH.write_text(json.dumps(processed, indent=2))

    return {"status": "processed", "email_id": email_id}

@app.get("/processed")
def get_processed():
    return load_json(PROCESSED_PATH) or {}


@app.post("/agent/query")
def agent_query_endpoint(
    email_id: int = Body(...),
    prompt_type: str = Body(...),
    user_instruction: str = Body(None)
):
    inbox = load_json(INBOX_PATH) or []
    email = next((e for e in inbox if e.get("id") == email_id), None)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    prompts = load_json(PROMPT_PATH) or {}

    key_map = {
        "categorization": "categorization_prompt",
        "action": "action_prompt",
        "auto_reply": "auto_reply_prompt",
        "reply": "auto_reply_prompt",
    }

    key = key_map.get(prompt_type)
    if not key:
        raise HTTPException(status_code=400, detail="Unknown prompt_type")

    template = prompts.get(key)
    out = llm_agent_query(email, template, user_instruction)

    try:
        parsed = json.loads(out)
    except:
        parsed = None

    return {"raw": out, "parsed": parsed}

# Create a new draft
@app.post("/drafts")
def create_draft(payload: dict = Body(...)):
    """
    Payload example:
    {
      "subject": "...",
      "body": "...",
      "source_email_id": 7,        # optional
      "type": "agent-generated"    # optional
      "metadata": { ... }          # optional
    }
    """
    drafts = load_json(DRAFTS_PATH) or []
    # create id
    new_id = str(uuid.uuid4())
    now = _now_iso()
    draft = {
        "id": new_id,
        "subject": payload.get("subject", ""),
        "body": payload.get("body", ""),
        "created_at": now,
        "updated_at": now,
        "source_email_id": payload.get("source_email_id"),
        "type": payload.get("type", "custom"),
        "metadata": payload.get("metadata", {})
    }
    drafts.append(draft)
    write_json_file(DRAFTS_PATH, drafts)
    return {"status": "ok", "draft": draft}

# List drafts
@app.get("/drafts")
def list_drafts():
    drafts = load_json(DRAFTS_PATH) or []
    return drafts

# Get a single draft by id
@app.get("/drafts/{draft_id}")
def get_draft(draft_id: str):
    drafts = load_json(DRAFTS_PATH) or []
    draft = next((d for d in drafts if d.get("id") == draft_id), None)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft

# Update a draft (partial updates supported)
@app.put("/drafts/{draft_id}")
def update_draft(draft_id: str, payload: dict = Body(...)):
    drafts = load_json(DRAFTS_PATH) or []
    idx = next((i for i,d in enumerate(drafts) if d.get("id") == draft_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    draft = drafts[idx]
    # update fields if provided
    if "subject" in payload:
        draft["subject"] = payload["subject"]
    if "body" in payload:
        draft["body"] = payload["body"]
    if "source_email_id" in payload:
        draft["source_email_id"] = payload.get("source_email_id")
    if "type" in payload:
        draft["type"] = payload.get("type")
    if "metadata" in payload:
        draft["metadata"] = payload.get("metadata")
    draft["updated_at"] = _now_iso()
    drafts[idx] = draft
    write_json_file(DRAFTS_PATH, drafts)
    return {"status": "ok", "draft": draft}

# (Optional) Delete a draft
@app.delete("/drafts/{draft_id}")
def delete_draft(draft_id: str):
    drafts = load_json(DRAFTS_PATH) or []
    new_list = [d for d in drafts if d.get("id") != draft_id]
    if len(new_list) == len(drafts):
        raise HTTPException(status_code=404, detail="Draft not found")
    write_json_file(DRAFTS_PATH, new_list)
    return {"status": "deleted", "id": draft_id}
