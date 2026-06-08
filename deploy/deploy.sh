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

[[ -z "$PROJECT" ]] && echo "ERROR: GOOGLE_CLOUD_PROJECT not set in retail_agent/.env" && exit 1

echo ""
echo "ADK A2UI Retail Agent — Agent Engine Deploy"
echo "  Project : $PROJECT"
echo "  Region  : $REGION"
echo ""

# ── Build deploy command ──────────────────────────────────────────────────────
DEPLOY_CMD=(
    adk deploy agent_engine
    --project="$PROJECT"
    --region="$REGION"
    --display_name="$DISPLAY_NAME"
    --description="ADK A2UI retail agent - Gemini + A2UI v0.9"
)

if [[ "${1:-}" == "--update" ]]; then
    [[ ! -f "$MANIFEST" ]] && echo "ERROR: $MANIFEST not found — run without --update first" && exit 1
    AGENT_ENGINE_ID=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['resource_id'])")
    echo "Updating resource: $AGENT_ENGINE_ID"
    DEPLOY_CMD+=(--agent_engine_id="$AGENT_ENGINE_ID")
    # Use Agent Engine's native session service — bypasses _validate_session_id
    # entirely, fixing the Agentspace resource path session_id error.
    DEPLOY_CMD+=(--session_service_uri="agentengine://$AGENT_ENGINE_ID")
else
    echo "Creating new deployment..."
fi

DEPLOY_CMD+=("$REPO_DIR/retail_agent")

# ── Run deploy and capture full output ───────────────────────────────────────
echo "Command: ${DEPLOY_CMD[*]}"
echo ""

# Tee to both terminal and capture file so we see live progress
OUTFILE=$(mktemp)
"${DEPLOY_CMD[@]}" 2>&1 | tee "$OUTFILE"
OUTPUT=$(cat "$OUTFILE"); rm -f "$OUTFILE"

# ── Extract resource name ─────────────────────────────────────────────────────
# Try multiple patterns — CLI output format varies by ADK version
RESOURCE_NAME=$(echo "$OUTPUT" | grep -oE 'projects/[^/]+/locations/[^/]+/reasoningEngines/[0-9]+' | head -1)

if [[ -z "$RESOURCE_NAME" ]]; then
    # Try alternate format: just the resource ID on its own line
    RESOURCE_ID=$(echo "$OUTPUT" | grep -oE '\b[0-9]{15,}\b' | head -1)
    if [[ -n "$RESOURCE_ID" ]]; then
        RESOURCE_NAME="projects/$PROJECT/locations/$REGION/reasoningEngines/$RESOURCE_ID"
        echo ""
        echo "Inferred resource name: $RESOURCE_NAME"
    else
        echo ""
        echo "WARNING: Could not parse resource name from deploy output."
        echo "Find it at: https://console.cloud.google.com/vertex-ai/agents?project=$PROJECT"
        echo ""
        echo "Then create deploy/deployment_manifest.json manually:"
        echo '{ "project_id": "'$PROJECT'", "location": "'$REGION'", "resource_id": "YOUR_ID", "resource_name": "projects/'$PROJECT'/locations/'$REGION'/reasoningEngines/YOUR_ID" }'
        exit 0
    fi
fi

RESOURCE_ID="${RESOURCE_NAME##*/}"

# ── Save manifest ─────────────────────────────────────────────────────────────
python3 -c "
import json, time
m = {
    'project_id':    '$PROJECT',
    'location':      '$REGION',
    'resource_name': '$RESOURCE_NAME',
    'resource_id':   '$RESOURCE_ID',
    'display_name':  '$DISPLAY_NAME',
    'deployed_at':   time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'query_url':     'https://$REGION-aiplatform.googleapis.com/v1/$RESOURCE_NAME:query',
}
open('$MANIFEST', 'w').write(json.dumps(m, indent=2))
print('Manifest saved: $MANIFEST')
"

echo ""
echo "Done!"
echo "  Resource : $RESOURCE_NAME"
echo "  Test     : python deploy/test.py"
echo "  Logs     : https://console.cloud.google.com/logs/query;query=resource.type%3D%22aiplatform.googleapis.com%2FReasoningEngine%22?project=$PROJECT"
