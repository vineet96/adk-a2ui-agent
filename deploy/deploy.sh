#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Deploy ADK A2UI Retail Agent to Vertex AI Agent Engine
# Uses the official ADK CLI — no Python SDK, no cloudpickle, no custom classes.
#
# Usage:
#   bash deploy/deploy.sh              # create new deployment
#   bash deploy/deploy.sh --update     # update existing deployment
#
# Prerequisites:
#   pip install google-adk --upgrade
#   gcloud auth application-default login
#   gcloud services enable aiplatform.googleapis.com cloudresourcemanager.googleapis.com
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$REPO_DIR/retail_agent/.env"
MANIFEST="$REPO_DIR/deploy/deployment_manifest.json"

# ── Load env vars ─────────────────────────────────────────────────────────────
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found"; exit 1
fi
set -a; source "$ENV_FILE"; set +a

PROJECT="${GOOGLE_CLOUD_PROJECT:-}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
DISPLAY_NAME="adk-a2ui-retail-agent"

if [[ -z "$PROJECT" ]]; then
  echo "ERROR: GOOGLE_CLOUD_PROJECT not set in retail_agent/.env"; exit 1
fi

echo ""
echo "ADK A2UI Retail Agent — Agent Engine Deploy"
echo "  Project : $PROJECT"
echo "  Region  : $REGION"
echo "  Agent   : $REPO_DIR/retail_agent"
echo ""

# ── Build deploy command ──────────────────────────────────────────────────────
DEPLOY_CMD=(
  adk deploy agent_engine
  --project="$PROJECT"
  --region="$REGION"
  --display_name="$DISPLAY_NAME"
)

# --update: pass existing agent_engine_id to update in-place
if [[ "${1:-}" == "--update" ]]; then
  if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: --update requires deploy/deployment_manifest.json"
    echo "       Run without --update first to create the initial deployment."
    exit 1
  fi
  AGENT_ENGINE_ID=$(python3 -c "import json; print(json.load(open('$MANIFEST'))['resource_id'])")
  echo "Updating resource ID: $AGENT_ENGINE_ID"
  DEPLOY_CMD+=(--agent_engine_id="$AGENT_ENGINE_ID")
else
  echo "Creating new deployment..."
fi

DEPLOY_CMD+=("$REPO_DIR/retail_agent")

# ── Deploy ────────────────────────────────────────────────────────────────────
echo "Running: ${DEPLOY_CMD[*]}"
echo ""

OUTPUT=$("${DEPLOY_CMD[@]}" 2>&1)
echo "$OUTPUT"

# ── Parse resource name from output and save manifest ────────────────────────
RESOURCE_NAME=$(echo "$OUTPUT" | grep -oP 'projects/[^\s]+/reasoningEngines/[0-9]+' | head -1)

if [[ -z "$RESOURCE_NAME" ]]; then
  echo ""
  echo "WARNING: Could not parse resource name from output."
  echo "Check the console: https://console.cloud.google.com/vertex-ai/agents?project=$PROJECT"
  exit 1
fi

RESOURCE_ID="${RESOURCE_NAME##*/}"

python3 - << PYEOF
import json, time
manifest = {
    "project_id":    "$PROJECT",
    "location":      "$REGION",
    "resource_name": "$RESOURCE_NAME",
    "resource_id":   "$RESOURCE_ID",
    "display_name":  "$DISPLAY_NAME",
    "deployed_at":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "query_url":     "https://$REGION-aiplatform.googleapis.com/v1/$RESOURCE_NAME:query",
}
with open("$MANIFEST", "w") as f:
    json.dump(manifest, f, indent=2)
print("Manifest saved to deploy/deployment_manifest.json")
PYEOF

echo ""
echo "Done!"
echo "  Resource : $RESOURCE_NAME"
echo "  ID       : $RESOURCE_ID"
echo ""
echo "Test:    python deploy/test.py"
echo "Monitor: https://console.cloud.google.com/vertex-ai/agents?project=$PROJECT"
echo "Logs:    https://console.cloud.google.com/logs/query;query=resource.type%3D%22aiplatform.googleapis.com%2FReasoningEngine%22?project=$PROJECT"
