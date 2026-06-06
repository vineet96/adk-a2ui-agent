#!/bin/bash
# Deploy ADK A2UI Retail Agent to Vertex AI Agent Engine
#
# Usage:
#   bash deploy/deploy.sh              # create new deployment
#   bash deploy/deploy.sh --update     # update existing deployment
#
# Prerequisites:
#   pip install "google-adk[a2a]" --upgrade
#   gcloud auth application-default login
#   gcloud services enable aiplatform.googleapis.com
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO_DIR/retail_agent/.env"
MANIFEST="$REPO_DIR/deploy/deployment_manifest.json"

# ── Load .env ─────────────────────────────────────────────────────────────────
[[ ! -f "$ENV_FILE" ]] && echo "ERROR: $ENV_FILE not found" && exit 1
set -a; source "$ENV_FILE"; set +a

PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
DISPLAY_NAME="adk-a2ui-retail-agent"

# Use the locally installed ADK version — ensures container matches local env.
ADK_VERSION=$(python3 -c "import importlib.metadata; print(importlib.metadata.version('google-adk'))" 2>/dev/null || echo "")

[[ -z "$PROJECT" ]] && echo "ERROR: GOOGLE_CLOUD_PROJECT not set in retail_agent/.env" && exit 1

echo ""
echo "ADK A2UI Retail Agent — Agent Engine Deploy"
echo "  Project     : $PROJECT"
echo "  Region      : $REGION"
echo "  ADK version : ${ADK_VERSION:-auto}"
echo ""

# ── Build command ─────────────────────────────────────────────────────────────
DEPLOY_CMD=(
    adk deploy agent_engine
    --project="$PROJECT"
    --region="$REGION"
    --display_name="$DISPLAY_NAME"
    --description="ADK A2UI retail agent - Gemini + A2UI v0.9"
)

# Pin the ADK version in the container to match local
[[ -n "$ADK_VERSION" ]] && DEPLOY_CMD+=(--adk_version="$ADK_VERSION")

# Point session service at Agent Engine so Gemini Enterprise session IDs
# are resolved correctly without hitting the local validator.
# This tells ADK to use Agent Engine's native session management,
# bypassing VertexAiSessionService._validate_session_id entirely.
if [[ "${1:-}" == "--update" ]]; then
    [[ ! -f "$MANIFEST" ]] && echo "ERROR: $MANIFEST not found — run without --update first" && exit 1
    AGENT_ENGINE_ID=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['resource_id'])")
    echo "Updating: $AGENT_ENGINE_ID"
    DEPLOY_CMD+=(--agent_engine_id="$AGENT_ENGINE_ID")
    DEPLOY_CMD+=(--session_service_uri="agentengine://$AGENT_ENGINE_ID")
fi

DEPLOY_CMD+=("$REPO_DIR/retail_agent")

# ── Deploy ────────────────────────────────────────────────────────────────────
echo "Running: ${DEPLOY_CMD[*]}"
echo ""
OUTPUT=$("${DEPLOY_CMD[@]}" 2>&1)
echo "$OUTPUT"

# ── Parse resource name ───────────────────────────────────────────────────────
RESOURCE_NAME=$(echo "$OUTPUT" | grep -oP 'projects/[^\s]+/reasoningEngines/[0-9]+' | head -1)

if [[ -z "$RESOURCE_NAME" ]]; then
    echo ""
    echo "WARNING: Could not parse resource name from output."
    echo "Check: https://console.cloud.google.com/vertex-ai/agents?project=$PROJECT"
    exit 1
fi

RESOURCE_ID="${RESOURCE_NAME##*/}"

python3 -c "
import json, time
manifest = {
    'project_id':    '$PROJECT',
    'location':      '$REGION',
    'resource_name': '$RESOURCE_NAME',
    'resource_id':   '$RESOURCE_ID',
    'display_name':  '$DISPLAY_NAME',
    'adk_version':   '${ADK_VERSION:-unknown}',
    'deployed_at':   time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'query_url':     'https://$REGION-aiplatform.googleapis.com/v1/$RESOURCE_NAME:query',
}
f = open('$MANIFEST', 'w')
json.dump(manifest, f, indent=2)
f.close()
print('Manifest saved.')
"
