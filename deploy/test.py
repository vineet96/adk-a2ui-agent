"""
Test the deployed ADK A2UI Retail Agent on Vertex AI Agent Engine.
Reads deploy/deployment_manifest.json produced by deploy/deploy.sh.

Usage:
    python deploy/test.py
    python deploy/test.py "vacuum cleaner"
"""

import json
import os
import sys
import time

# ── Load manifest ─────────────────────────────────────────────────────────────
MANIFEST = os.path.join(os.path.dirname(__file__), "deployment_manifest.json")
if not os.path.exists(MANIFEST):
    print("ERROR: deployment_manifest.json not found.")
    print("       Run deploy/deploy.sh first.")
    sys.exit(1)

with open(MANIFEST) as f:
    m = json.load(f)

PROJECT       = m["project_id"]
LOCATION      = m["location"]
RESOURCE_NAME = m["resource_name"]
RESOURCE_ID   = m["resource_id"]
QUERY         = sys.argv[1] if len(sys.argv) > 1 else "wireless headphones"

print(f"""
Testing Agent Engine Deployment
  Resource : {RESOURCE_NAME}
  Query    : {QUERY}
""")

# ── Connect ───────────────────────────────────────────────────────────────────
import vertexai
from vertexai import agent_engines

vertexai.init(project=PROJECT, location=LOCATION)
remote_agent = agent_engines.get(RESOURCE_NAME)

# ── Create session ────────────────────────────────────────────────────────────
# Use a simple user_id — let Agent Engine manage session creation internally.
user_id = f"test-{int(time.time())}"
session = remote_agent.create_session(user_id=user_id)

# session ID may be a full resource path — extract the bare ID
raw_id = session["id"] if isinstance(session, dict) else session.id
session_id = raw_id.split("/")[-1] if "/" in str(raw_id) else str(raw_id)
print(f"Session: {session_id}\n")

# ── Query ─────────────────────────────────────────────────────────────────────
# Use stream_query — the correct method for ADK agents on Agent Engine.
# Do NOT pass session_id as a full resource path; use the bare ID only.
print(f"Querying: '{QUERY}'")
start = time.time()

parts = []
event_count = 0
for event in remote_agent.stream_query(
    user_id=user_id,
    session_id=session_id,
    message=QUERY,
):
    event_count += 1
    if isinstance(event, dict):
        for p in event.get("content", {}).get("parts", []):
            if isinstance(p, dict) and "text" in p:
                parts.append(p["text"])
    elif hasattr(event, "content") and event.content:
        for p in event.content.parts or []:
            if hasattr(p, "text") and p.text:
                parts.append(p.text)

elapsed = time.time() - start
raw = "".join(parts)

print(f"Received {event_count} event(s) in {elapsed:.1f}s\n")

# ── Parse A2UI ────────────────────────────────────────────────────────────────
s = raw.find("<a2ui-json>")
e = raw.find("</a2ui-json>")

if not raw:
    print("EMPTY RESPONSE")
    print("Check logs:")
    print(f"https://console.cloud.google.com/logs/query;query=resource.type%3D%22aiplatform.googleapis.com%2FReasoningEngine%22?project={PROJECT}")
elif s != -1 and e != -1:
    try:
        msgs = json.loads(raw[s + len("<a2ui-json>"):e].strip())
        print(f"A2UI messages: {len(msgs)}")
        for i, msg in enumerate(msgs):
            t = next((k for k in msg if k != "version"), "?")
            print(f"  [{i+1}] {t}")
            if t == "updateDataModel":
                products = msg.get("updateDataModel", {}).get("value", {}).get("products", [])
                for p in products:
                    print(f"       - {p.get('name')} {p.get('price')}")
    except json.JSONDecodeError as ex:
        print(f"JSON parse error: {ex}")
        print(raw[:500])
else:
    print("No <a2ui-json> block found in response.")
    print("Raw response:")
    print(raw[:1000])
