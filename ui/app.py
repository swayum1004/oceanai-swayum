# ui/app.py
import streamlit as st
import requests
import json
from datetime import datetime

st.set_page_config(page_title="Email Productivity Agent", layout="wide")
st.title("Email Productivity Agent — Prototype")

# -------------------------
# Sidebar: Settings & Prompts
# -------------------------
st.sidebar.header("Settings")
BACKEND = st.sidebar.text_input("Backend URL", value="http://127.0.0.1:8000")

st.sidebar.markdown("---")
st.sidebar.header("Prompt Brain (edit & save)")
try:
    resp = requests.get(f"{BACKEND}/prompts", timeout=3)
    prompts = resp.json()
except Exception:
    prompts = {
        "categorization_prompt": "Categorize the email into: Important, Newsletter, Spam, To-Do, Meeting, Personal. Return JSON: {\"category\":\"...\",\"reason\":\"...\"}\\n\\nEmail:\\n{email_text}",
        "action_prompt": "Extract tasks as JSON array with fields {\"task\",\"deadline\",\"assignee\",\"context\"}.\\n\\nEmail:\\n{email_text}",
        "auto_reply_prompt": "Draft a reply. Use {user_instruction} for tone. Return JSON: {\"subject\":\"...\",\"body\":\"...\"}\\n\\nEmail:\\n{email_text}"
    }

cat_prompt = st.sidebar.text_area("Categorization Prompt", prompts.get("categorization_prompt", ""), height=140)
act_prompt = st.sidebar.text_area("Action Item Prompt", prompts.get("action_prompt", ""), height=140)
auto_prompt = st.sidebar.text_area("Auto Reply Prompt", prompts.get("auto_reply_prompt", ""), height=140)

if st.sidebar.button("Save Prompts"):
    payload = {"categorization_prompt": cat_prompt, "action_prompt": act_prompt, "auto_reply_prompt": auto_prompt}
    try:
        r = requests.post(f"{BACKEND}/prompts", json=payload, timeout=3)
        if r.ok:
            st.sidebar.success("Prompts saved")
        else:
            st.sidebar.error("Save failed: " + r.text)
    except Exception as e:
        st.sidebar.error("Save failed: " + str(e))

st.sidebar.markdown("---")
st.sidebar.markdown("Assignment spec (local file):")
st.sidebar.code("/mnt/data/Assignment - 2.pdf")

# -------------------------
# Layout: Inbox / Right column
# -------------------------
col_inbox, col_right = st.columns((2, 1))

with col_inbox:
    st.header("Inbox")
    if st.button("Load Inbox"):
        try:
            r = requests.get(f"{BACKEND}/inbox", timeout=5)
            st.session_state["inbox"] = r.json()
            st.success(f"Loaded {len(st.session_state['inbox'])} emails")
        except Exception as e:
            st.error("Failed to load inbox: " + str(e))

    inbox = st.session_state.get("inbox", [])
    if not inbox:
        st.info("Click 'Load Inbox' to fetch mock emails from the backend.")
    else:
        # Iterate emails
        for email in inbox:
            eid = email.get("id")
            with st.expander(f"{email.get('subject')} — {email.get('sender')}"):
                st.write("Timestamp:", email.get("timestamp"))
                st.write(email.get("body"))

                btn_col1, btn_col2, btn_col3 = st.columns([1,1,1])
                if btn_col1.button("Process", key=f"proc-{eid}"):
                    try:
                        r = requests.post(f"{BACKEND}/process/{eid}", timeout=10)
                        if r.ok:
                            st.success("Processed. Click 'Show saved processed' or Refresh processed file on the right.")
                        else:
                            st.error("Processing failed: " + r.text)
                    except Exception as e:
                        st.error("Processing failed: " + str(e))

                if btn_col2.button("Show saved processed", key=f"showp-{eid}"):
                    try:
                        p = requests.get(f"{BACKEND}/processed", timeout=5).json()
                        item = p.get(str(eid), {})
                        if item:
                            st.subheader("Processed Output")
                            st.write("Category output (raw):")
                            st.code(item.get("category_output"))
                            st.write("Action output (raw):")
                            st.code(item.get("action_output"))
                        else:
                            st.info("No processed output saved for this email yet.")
                    except Exception as e:
                        st.error("Failed to fetch processed: " + str(e))

                # **************** Agent panel ****************
                st.markdown("**Agent**")
                ag_c1, ag_c2, ag_c3 = st.columns([1,1,2])

                # helper to call agent and display results (and return parsed output)
                def call_agent_and_show(email_id, prompt_type, user_instruction=None):
                    payload = {"email_id": email_id, "prompt_type": prompt_type}
                    if user_instruction is not None:
                        payload["user_instruction"] = user_instruction
                    try:
                        r = requests.post(f"{BACKEND}/agent/query", json=payload, timeout=15)
                        if not r.ok:
                            st.error("Agent call failed: " + r.text)
                            return None
                        resp = r.json()
                        st.write("Raw:")
                        st.code(resp.get("raw"))
                        st.write("Parsed:")
                        st.json(resp.get("parsed"))
                        return resp.get("parsed")
                    except Exception as e:
                        st.error("Agent call failed: " + str(e))
                        return None

                if ag_c1.button("Summarize", key=f"summ-{eid}"):
                    call_agent_and_show(eid, "categorization", "summarize")

                if ag_c2.button("What tasks?", key=f"tasks-{eid}"):
                    call_agent_and_show(eid, "action")

                # Draft reply quick button: show parsed then offer Save as Draft
                if ag_c3.button("Draft Reply (friendly)", key=f"draft-{eid}"):
                    parsed = call_agent_and_show(eid, "auto_reply", "friendly")
                    # If parsed contains subject/body, show Save as Draft button
                    if isinstance(parsed, dict) and parsed.get("subject") and parsed.get("body"):
                        # show a confirmation + Save button
                        st.success("Agent generated a draft. Click Save below to store it.")
                        if st.button("Save agent reply as draft", key=f"save-draft-{eid}"):
                            draft_payload = {
                                "subject": parsed.get("subject"),
                                "body": parsed.get("body"),
                                "source_email_id": eid,
                                "type": "agent-generated",
                                "metadata": {"source": "agent", "generated_at": datetime.utcnow().isoformat()}
                            }
                            try:
                                rd = requests.post(f"{BACKEND}/drafts", json=draft_payload, timeout=5)
                                if rd.ok:
                                    st.success("Draft saved.")
                                else:
                                    st.error("Failed to save draft: " + rd.text)
                            except Exception as e:
                                st.error("Failed to save draft: " + str(e))

                # Custom query
                st.markdown("**Custom Agent Query**")
                user_q = st.text_input(f"Instruction for email {eid}", key=f"custom-{eid}")
                cq1, cq2 = st.columns([1,1])
                if cq1.button("Ask Agent", key=f"ask-{eid}"):
                    if not user_q.strip():
                        st.warning("Enter a custom instruction.")
                    else:
                        # use auto_reply prompt when user_instruction is provided
                        call_agent_and_show(eid, "auto_reply", user_q)

with col_right:
    # Processed viewer + Drafts manager
    st.header("Processed & Drafts")
    if st.button("Refresh processed file"):
        try:
            p = requests.get(f"{BACKEND}/processed", timeout=5).json()
            st.session_state["processed"] = p
            st.success("Loaded processed data")
        except Exception as e:
            st.error("Failed to load processed data: " + str(e))

    processed = st.session_state.get("processed", {})
    if processed:
        st.subheader("Processed emails")
        for k, v in (processed.items() if isinstance(processed, dict) else []):
            subj = "-"
            try:
                if isinstance(v, dict) and v.get("email"):
                    subj = v["email"].get("subject", "-")
            except Exception:
                subj = "-"
            st.markdown(f"**Email ID: {k} — {subj}**")
            st.write("Category (raw):")
            st.code(v.get("category_output") if isinstance(v, dict) else str(v))
            st.write("Actions (raw):")
            st.code(v.get("action_output") if isinstance(v, dict) else "-")
            st.markdown("---")
    else:
        st.info("No processed data loaded. Click 'Refresh processed file' after processing emails.")

    st.markdown("### Drafts")
    if st.button("Refresh drafts"):
        try:
            drafts = requests.get(f"{BACKEND}/drafts", timeout=5).json()
            st.session_state["drafts"] = drafts
            st.success("Loaded drafts")
        except Exception as e:
            st.error("Failed to load drafts: " + str(e))

    drafts = st.session_state.get("drafts", [])
    if drafts:
        for d in drafts:
            st.markdown(f"**{d.get('subject','(no subject)')}** — id: {d.get('id')}")
            st.write("Last updated:", d.get("updated_at"))
            st.write(d.get("body"))
            dcols = st.columns([1,1,1])
            # Edit opens a small editor inline
            if dcols[0].button("Edit", key=f"edit-{d.get('id')}"):
                # open edit modal (simple inline editor)
                new_subject = st.text_input(f"Edit subject {d.get('id')}", value=d.get("subject"), key=f"es-{d.get('id')}")
                new_body = st.text_area(f"Edit body {d.get('id')}", value=d.get("body"), key=f"eb-{d.get('id')}", height=200)
                if st.button("Save changes", key=f"save-{d.get('id')}"):
                    payload = {"subject": new_subject, "body": new_body}
                    try:
                        upd = requests.put(f"{BACKEND}/drafts/{d.get('id')}", json=payload, timeout=5)
                        if upd.ok:
                            st.success("Draft updated")
                        else:
                            st.error("Update failed: " + upd.text)
                    except Exception as e:
                        st.error("Update failed: " + str(e))
            if dcols[1].button("Load to composer", key=f"load-{d.get('id')}"):
                # store in session composer
                st.session_state["composer_subject"] = d.get("subject")
                st.session_state["composer_body"] = d.get("body")
                st.success("Loaded into composer")
            if dcols[2].button("Delete", key=f"del-{d.get('id')}"):
                try:
                    rd = requests.delete(f"{BACKEND}/drafts/{d.get('id')}", timeout=5)
                    if rd.ok:
                        st.success("Draft deleted")
                        # refresh drafts list
                        st.session_state.pop("drafts", None)
                    else:
                        st.error("Delete failed: " + rd.text)
                except Exception as e:
                    st.error("Delete failed: " + str(e))
            st.markdown("---")
    else:
        st.info("No drafts loaded. Click 'Refresh drafts' to load saved drafts.")

    # Composer for new drafts or editing loaded draft content
    st.markdown("### Composer (create new draft)")
    cs = st.text_input("Subject", value=st.session_state.get("composer_subject",""))
    cb = st.text_area("Body", value=st.session_state.get("composer_body",""), height=200)
    c1, c2 = st.columns([1,1])
    if c1.button("Save as new draft"):
        payload = {"subject": cs, "body": cb, "type": "custom"}
        try:
            r = requests.post(f"{BACKEND}/drafts", json=payload, timeout=5)
            if r.ok:
                st.success("Draft saved")
                # clear composer
                st.session_state.pop("composer_subject", None)
                st.session_state.pop("composer_body", None)
            else:
                st.error("Save failed: " + r.text)
        except Exception as e:
            st.error("Save failed: " + str(e))
    if c2.button("Clear composer"):
        st.session_state.pop("composer_subject", None)
        st.session_state.pop("composer_body", None)
        st.success("Cleared composer")

st.markdown("---")
st.info("Notes: Drafts are saved to backend via /drafts endpoints. The assignment spec is available locally at /mnt/data/Assignment - 2.pdf.")
