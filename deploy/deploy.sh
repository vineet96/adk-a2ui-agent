#!/bin/bash
# Deploy ADK A2UI Retail Agent to Vertex AI Agent Engine
#
# Usage:
#   bash deploy/deploy.sh              # create new deployment
#   bash deploy/deploy.sh --update     # update existing deployment
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO_DIR/retail_agent/.env"
MANIFEST="$REPO_DIR/deploy/deployment_manifest.json"
AGENT_DIR="$REPO_DIR/retail_agent"
CONFIG_FILE="$AGENT_DIR/.agent_engine_config.json"

# ── Load .env ─────────────────────────────────────────────────────────────────
[[ ! -f "$ENV_FILE" ]] && echo "ERROR: $ENV_FILE not found" && exit 1
set -a; source "$ENV_FILE"; set +a

PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
DISPLAY_NAME="adk-a2ui-retail-agent"

[[ -z "$PROJECT" ]] && echo "ERROR: GOOGLE_CLOUD_PROJECT not set in retail_agent/.env" && exit 1

# ── Detect available CLI flags ────────────────────────────────────────────────
ADK_VERSION=$(adk --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
HAS_ENGINE_ID=$(adk deploy agent_engine --help 2>&1 | grep -c "agent_engine_id" || true)
HAS_SESSION_URI=$(adk deploy agent_engine --help 2>&1 | grep -c "session_service_uri" || true)

echo ""
echo "ADK A2UI Retail Agent — Agent Engine Deploy"
echo "  Project     : $PROJECT"
echo "  Region      : $REGION"
echo "  ADK version : $ADK_VERSION"
echo ""

# ── Build base command ────────────────────────────────────────────────────────
DEPLOY_CMD=(
    adk deploy agent_engine
    --project="$PROJECT"
    --region="$REGION"
    --display_name="$DISPLAY_NAME"
    --description="ADK A2UI retail agent - Gemini + A2UI v0.9"
)

# ── Update mode ───────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--update" ]]; then
    [[ ! -f "$MANIFEST" ]] && echo "ERROR: $MANIFEST not found — run without --update first" && exit 1
    AGENT_ENGINE_ID=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['resource_id'])")
    echo "Updating resource: $AGENT_ENGINE_ID"

    if [[ "$HAS_ENGINE_ID" -gt 0 ]]; then
        # Newer ADK: --agent_engine_id flag available
        DEPLOY_CMD+=(--agent_engine_id="$AGENT_ENGINE_ID")
    else
        # Older ADK: write .agent_engine_config.json instead
        echo "Using .agent_engine_config.json for update (ADK $ADK_VERSION)"
        python3 -c "
import json
cfg = {
    'agent_engine_id': '$AGENT_ENGINE_ID',
    'project': '$PROJECT',
    'region': '$REGION',
}
open('$CONFIG_FILE', 'w').write(json.dumps(cfg, indent=2))
print('Wrote $CONFIG_FILE')
"
    fi

    # Use Agent Engine native sessions if supported — fixes Agentspace session_id
    if [[ "$HAS_SESSION_URI" -gt 0 ]]; then
        DEPLOY_CMD+=(--session_service_uri="agentengine://$AGENT_ENGINE_ID")
    fi
else
    echo "Creating new deployment..."
fi

DEPLOY_CMD+=("$AGENT_DIR")

# ── Run ───────────────────────────────────────────────────────────────────────
echo "Running: ${DEPLOY_CMD[*]}"
echo ""

OUTFILE=$(mktemp)
"${DEPLOY_CMD[@]}" 2>&1 | tee "$OUTFILE" || true
OUTPUT=$(cat "$OUTFILE"); rm -f "$OUTFILE"

# Clean up config file after deploy
[[ -f "$CONFIG_FILE" ]] && rm -f "$CONFIG_FILE"

# ── Parse resource name ───────────────────────────────────────────────────────
RESOURCE_NAME=$(echo "$OUTPUT" | grep -oE 'projects/[^/]+/locations/[^/]+/reasoningEngines/[0-9]+' | head -1)

if [[ -z "$RESOURCE_NAME" ]]; then
    RESOURCE_ID=$(echo "$OUTPUT" | grep -oE '\b[0-9]{15,}\b' | head -1)
    if [[ -n "$RESOURCE_ID" ]]; then
        RESOURCE_NAME="projects/$PROJECT/locations/$REGION/reasoningEngines/$RESOURCE_ID"
    else
        echo ""
        echo "Deploy output did not contain a resource name."
        echo "Check: https://console.cloud.google.com/vertex-ai/agents?project=$PROJECT"
        echo ""
        echo "If deployed successfully, create $MANIFEST manually:"
        echo "  python3 deploy/save_manifest.py YOUR_RESOURCE_ID"
        exit 0
    fi
fi

RESOURCE_ID="${RESOURCE_NAME##*/}"
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
print('Manifest: $MANIFEST')
"

echo ""
echo "Done! Resource: $RESOURCE_NAME"
echo "Test : python deploy/test.py"
echo "Logs : https://console.cloud.google.com/logs/query;query=resource.type%3D%22aiplatform.googleapis.com%2FReasoningEngine%22?project=$PROJECT"
