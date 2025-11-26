# backend/llm.py
import os
import json
import re
from typing import Optional, Dict, Any

# ---- Local model loader (Hugging Face transformers) ----
def use_local_model() -> bool:
    """
    Enable local HF model when environment variable LOCAL_LLM=1
    """
    return os.environ.get("LOCAL_LLM", "0") == "1"

def _load_transformer_model(model_name: str = "distilgpt2"):
    """
    Load a transformers pipeline for text-generation.
    This function tries to use GPU if available and configured.
    """
    try:
        from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
        import torch
    except Exception as e:
        raise RuntimeError("transformers or torch not installed: " + str(e))

    # device
    device = 0 if torch.cuda.is_available() else -1

    # load tokenizer and model
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # for some tokenizers (e.g., LLaMA variants) you may need trust_remote_code=True
    model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto" if device == 0 else None, torch_dtype=(torch.float16 if device == 0 else torch.float32), low_cpu_mem_usage=True)
    gen = pipeline("text-generation", model=model, tokenizer=tokenizer, device=device)
    return gen

def call_local_model(prompt: str, max_tokens: int = 256, model_name: str = None) -> Optional[str]:
    """
    Try to generate text using a local HF model. Returns string output or None on failure.
    Set environment var LOCAL_MODEL_NAME to choose a model (default: distilgpt2).
    """
    try:
        model_name = model_name or os.environ.get("LOCAL_MODEL_NAME", "distilgpt2")
        gen = _load_transformer_model(model_name)
        out = gen(prompt, max_new_tokens=max_tokens, do_sample=True, temperature=0.7)
        if isinstance(out, list) and len(out) > 0 and "generated_text" in out[0]:
            return out[0]["generated_text"]
        # fallback flatten
        return str(out)
    except Exception as e:
        # do not raise — let caller fall back to mock
        print("Local model generation failed:", e)
        return None

# ---- Mock helpers (will run when local model not available) ----
def _simple_json_safe(s: str) -> str:
    return s.replace('\n', ' ').strip()

def _mock_categorize(email_text: str) -> Dict[str, str]:
    t = email_text.lower()
    if any(x in t for x in ["invoice", "payment", "due", "bill"]):
        return {"category": "Important", "reason": "Contains payment/invoice information."}
    if any(x in t for x in ["prize", "winner", "click here", "claim"]):
        return {"category": "Spam", "reason": "Typical spam phrases detected."}
    if any(x in t for x in ["newsletter", "digest", "weekly", "unsubscribe"]):
        return {"category": "Newsletter", "reason": "Likely a newsletter or digest."}
    if any(x in t for x in ["meet", "meeting", "schedule", "agenda", "availability"]):
        return {"category": "Meeting", "reason": "Requests scheduling a meeting."}
    if any(x in t for x in ["please", "can you", "could you", "please do", "action"]):
        return {"category": "To-Do", "reason": "Contains a direct request for action."}
    return {"category": "Personal", "reason": "No clear request detected; treat as personal/info."}

def _mock_extract_actions(email_text: str) -> list:
    import re
    t = email_text
    tasks = []
    if re.search(r'(please|kindly|could you|can you|need you to|we need)', t, re.I):
        m = re.search(r'(?:please|kindly|could you|can you|we need to|we need)\s+([^\\.|\\n]+)', t, re.I)
        if m:
            task_text = m.group(1).strip()
            tasks.append({"task": _simple_json_safe(task_text), "deadline": None, "assignee": None, "context": _simple_json_safe(t)})
    if re.search(r'(meet|meeting|schedule|proposed agenda|proposed time|availability)', t, re.I):
        tasks.append({"task": "Schedule meeting / confirm time", "deadline": None, "assignee": None, "context": _simple_json_safe(t)})
    if re.search(r'(invoice|payment|due)', t, re.I):
        tasks.append({"task": "Review invoice / arrange payment", "deadline": None, "assignee": None, "context": _simple_json_safe(t)})
    return tasks

def _mock_draft_reply(email_text: str, user_instruction: Optional[str] = None) -> Dict[str, str]:
    t = email_text.lower()
    subject = "Re: " + (_simple_json_safe(email_text[:40]) + "..." if len(email_text) > 40 else _simple_json_safe(email_text))
    body_lines = []
    if re.search(r'(meeting|meet|schedule)', t):
        body_lines.append("Thanks for the invite — I'm available for a 30-minute meeting. Could you share the agenda?")
        body_lines.append("Proposed times: Tue 10:00 or Wed 14:00. Do either work for you?")
    elif re.search(r'(invoice|payment|due)', t):
        body_lines.append("Thanks — I see the invoice. We'll process payment within the stated terms.")
        body_lines.append("If you need anything else, let me know.")
    else:
        body_lines.append("Thanks for the message. Could you provide a bit more detail so I can help?")
    if user_instruction:
        body_lines.append("")
        body_lines.append("Tone requested: " + user_instruction)
    return {"subject": subject, "body": " ".join(body_lines)}

# ---- Public API ----
def call_llm(prompt: str, max_tokens: int = 256) -> str:
    """
    Try local HF model if enabled. Otherwise use mock heuristics.
    """
    if use_local_model():
        out = call_local_model(prompt, max_tokens=max_tokens)
        if out:
            return out

    pl = prompt.lower()
    if "categorize" in pl or "category" in pl:
        return json.dumps(_mock_categorize(prompt))
    if "extract" in pl and ("task" in pl or "action" in pl):
        return json.dumps(_mock_extract_actions(prompt))
    if "draft" in pl or "reply" in pl or "auto-reply" in pl:
        # try to find user instruction
        ui = None
        m = re.search(r'user instruction[:\\s]*([^\\n\\{]+)', prompt, re.I)
        if m:
            ui = m.group(1).strip()
        return json.dumps(_mock_draft_reply(prompt, user_instruction=ui))
    return '"MOCK_LLM: no match for prompt; implement local model for better output."'

def agent_query(email: Dict[str, Any], prompt_template: str, user_instruction: Optional[str] = None) -> str:
    text = email.get("body", "") + "\\n\\nFull email metadata:\\n" + json.dumps(email)
    prompt = prompt_template.replace("{email_text}", text)
    if user_instruction is not None:
        prompt = prompt.replace("{user_instruction}", user_instruction)
    return call_llm(prompt)
