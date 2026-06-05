# ADK A2UI Retail Agent

Retail product search agent built with **Google ADK 2.0** and **Gemini**,
returning **A2UI v0.9** generative UI instead of plain text.

Deployed to **Vertex AI Agent Engine** using the **ADK CLI** — the officially
supported deployment path, avoiding all cloudpickle/serialization issues.

---

## Project Structure

```
adk-a2ui-agent/
├── retail_agent/         ← ADK agent (what gets deployed)
│   ├── __init__.py
│   ├── agent.py          ← root_agent definition + tools
│   └── .env              ← GOOGLE_CLOUD_PROJECT, MODEL, etc.
├── client/
│   └── index.html        ← A2UI surface renderer (no build step)
├── deploy/
│   ├── deploy.sh         ← deploys via adk deploy agent_engine
│   ├── test.py           ← tests the deployed agent
│   └── deployment_manifest.json  ← auto-generated after deploy
└── README.md
```

---

## Local Development

### 1. Install ADK

```bash
pip install google-adk --upgrade
```

### 2. Configure `.env`

Edit `retail_agent/.env`:

```env
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
MODEL=gemini-2.5-flash
```

### 3. Authenticate

```bash
gcloud auth application-default login
gcloud config set project your-gcp-project-id
```

### 4. Run locally

```bash
# Interactive terminal
adk run retail_agent

# Web UI at http://localhost:8000
adk web retail_agent
```

---

## Deploy to Agent Engine

### Prerequisites

```bash
# Enable required APIs
gcloud services enable aiplatform.googleapis.com cloudresourcemanager.googleapis.com
```

### First deploy

```bash
bash deploy/deploy.sh
```

This runs `adk deploy agent_engine` which packages the `retail_agent/` folder,
builds a container via Cloud Build, and deploys to Agent Engine.
Takes ~5 minutes. Saves the resource ID to `deploy/deployment_manifest.json`.

### Update existing deployment

```bash
bash deploy/deploy.sh --update
```

Reads the resource ID from `deployment_manifest.json` and passes it via
`--agent_engine_id` to update the same Agent Engine instance in-place.

### Test the deployed agent

```bash
python deploy/test.py
python deploy/test.py "noise cancelling headphones"
```

---

## A2UI Response Format

The agent wraps every response in `<a2ui-json>` tags containing exactly
3 messages:

```json
[
  { "version": "v0.9", "createSurface": { "surfaceId": "products", "catalogId": "..." } },
  { "version": "v0.9", "updateComponents": { "surfaceId": "products", "components": [...] } },
  { "version": "v0.9", "updateDataModel": { "surfaceId": "products", "path": "/", "value": {...} } }
]
```

The client (`client/index.html`) parses these messages and renders
native HTML components — no build step required.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_CLOUD_PROJECT` | Yes | GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | No | Region (default: us-central1) |
| `GOOGLE_GENAI_USE_VERTEXAI` | Yes | Must be `true` for Agent Engine |
| `MODEL` | No | Gemini model (default: gemini-2.5-flash) |

---

## References

- ADK deploy docs: https://google.github.io/adk-docs/deploy/agent-engine/deploy/
- Agent Engine: https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview
- A2UI spec: https://a2ui.org/concepts/overview/
