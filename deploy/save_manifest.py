"""
Manually save deployment_manifest.json after a successful deploy.
Use this if deploy.sh couldn't parse the resource ID from the output.

Usage:
    python deploy/save_manifest.py RESOURCE_ID
    python deploy/save_manifest.py 4019456620114214912
"""
import json, os, sys, time

if len(sys.argv) < 2:
    print("Usage: python deploy/save_manifest.py RESOURCE_ID")
    sys.exit(1)

ENV_FILE = os.path.join(os.path.dirname(__file__), "..", "retail_agent", ".env")
project, region = "", "us-central1"

if os.path.exists(ENV_FILE):
    for line in open(ENV_FILE):
        line = line.strip()
        if line.startswith("GOOGLE_CLOUD_PROJECT="):
            project = line.split("=", 1)[1]
        elif line.startswith("GOOGLE_CLOUD_LOCATION="):
            region = line.split("=", 1)[1]

resource_id   = sys.argv[1].strip()
resource_name = f"projects/{project}/locations/{region}/reasoningEngines/{resource_id}"

manifest = {
    "project_id":    project,
    "location":      region,
    "resource_name": resource_name,
    "resource_id":   resource_id,
    "display_name":  "adk-a2ui-retail-agent",
    "deployed_at":   time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "query_url":     f"https://{region}-aiplatform.googleapis.com/v1/{resource_name}:query",
}

out = os.path.join(os.path.dirname(__file__), "deployment_manifest.json")
with open(out, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"Saved: {out}")
print(f"  Resource: {resource_name}")
print(f"\nTest: python deploy/test.py")
