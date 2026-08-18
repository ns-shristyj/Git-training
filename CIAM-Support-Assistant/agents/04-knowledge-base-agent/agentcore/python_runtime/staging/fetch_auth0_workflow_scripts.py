"""
Fetch real Auth0 Actions/Rules scripts using the workflow-reader M2M app
and generate a Knowledge Base markdown document from them.

Credentials: AWS Secrets Manager at ciam-agent/auth0-workflows
Auth0 domain: netskope-dev.us.auth0.com
Required scopes on the M2M app: read:actions, read:rules, read:triggers
"""

import json
import boto3
import requests

AWS_REGION = "us-east-1"
AUTH0_DOMAIN = "netskope-dev.us.auth0.com"
SECRET_PATH = "ciam-agent/auth0-workflows"

print("=" * 80)
print("FETCH AUTH0 WORKFLOW SCRIPTS (Actions + Rules)")
print("=" * 80)
print()

# Step 1: Get credentials from Secrets Manager
print("Step 1: Retrieving credentials from Secrets Manager...")
client = boto3.client("secretsmanager", region_name=AWS_REGION)
secret = json.loads(client.get_secret_value(SecretId=SECRET_PATH)["SecretString"])
print(f"✅ Retrieved client_id: {secret['client_id'][:8]}...")
print()

# Step 2: Get M2M access token
print("Step 2: Acquiring Auth0 Management API token...")
token_resp = requests.post(
    f"https://{AUTH0_DOMAIN}/oauth/token",
    json={
        "grant_type": "client_credentials",
        "client_id": secret["client_id"],
        "client_secret": secret["client_secret"],
        "audience": f"https://{AUTH0_DOMAIN}/api/v2/",
    },
    timeout=10,
)

if token_resp.status_code != 200:
    print(f"❌ Token acquisition failed: {token_resp.status_code}")
    print(token_resp.text)
    exit(1)

access_token = token_resp.json()["access_token"]
print(f"✅ Token acquired")
print()

headers = {"Authorization": f"Bearer {access_token}"}

# Step 3: Fetch Actions
print("Step 3: Fetching Auth0 Actions...")
actions_resp = requests.get(
    f"https://{AUTH0_DOMAIN}/api/v2/actions/actions",
    headers=headers,
    timeout=10,
)

actions = []
if actions_resp.status_code == 200:
    actions = actions_resp.json().get("actions", [])
    print(f"✅ Found {len(actions)} action(s)")
else:
    print(f"⚠️  Actions fetch failed: {actions_resp.status_code} - {actions_resp.text[:200]}")
print()

# Step 4: Fetch Rules (legacy, may be empty if tenant only uses Actions)
print("Step 4: Fetching Auth0 Rules (legacy)...")
rules_resp = requests.get(
    f"https://{AUTH0_DOMAIN}/api/v2/rules",
    headers=headers,
    timeout=10,
)

rules = []
if rules_resp.status_code == 200:
    rules = rules_resp.json()
    print(f"✅ Found {len(rules)} rule(s)")
else:
    print(f"⚠️  Rules fetch failed: {rules_resp.status_code} - {rules_resp.text[:200]}")
print()

# Step 5: Fetch full code for each action
print("Step 5: Fetching full script code for each Action...")
detailed_actions = []
for action in actions:
    action_id = action.get("id")
    detail_resp = requests.get(
        f"https://{AUTH0_DOMAIN}/api/v2/actions/actions/{action_id}",
        headers=headers,
        timeout=10,
    )
    if detail_resp.status_code == 200:
        detailed_actions.append(detail_resp.json())
        print(f"  ✅ {action.get('name', action_id)}")
    else:
        print(f"  ⚠️  Failed to fetch detail for {action_id}: {detail_resp.status_code}")

print()

# Step 6: Build markdown KB document
print("Step 6: Generating Knowledge Base document...")

md_lines = [
    "# Auth0 Workflow Scripts (Actions & Rules)",
    "",
    "> **Source:** Live Auth0 Management API (netskope-dev.us.auth0.com)",
    "> Fetched via CIAM Knowledge Base Agent's workflow-reader M2M app.",
    "",
    "This document maps each Auth0 Action/Rule to what it does, when it runs,",
    "and its actual script logic — used by Agent 4 Tool 4 (identify_failing_workflow)",
    "to map a failure symptom to the real script responsible.",
    "",
]

if detailed_actions:
    md_lines.append("## Actions")
    md_lines.append("")
    for action in detailed_actions:
        name = action.get("name", "Unnamed Action")
        supported_triggers = action.get("supported_triggers", [])
        trigger_ids = [t.get("id") for t in supported_triggers]
        status = action.get("status", "unknown")
        code = action.get("code", "")

        md_lines.append(f"### {name}")
        md_lines.append("")
        md_lines.append(f"- **Trigger(s):** {', '.join(trigger_ids) if trigger_ids else 'N/A'}")
        md_lines.append(f"- **Status:** {status}")
        md_lines.append(f"- **Action ID:** {action.get('id')}")
        md_lines.append("")
        md_lines.append("**Script:**")
        md_lines.append("```javascript")
        md_lines.append(code if code else "// No code returned")
        md_lines.append("```")
        md_lines.append("")
else:
    md_lines.append("## Actions")
    md_lines.append("")
    md_lines.append("_No actions found or fetch failed — see fetch log above._")
    md_lines.append("")

if rules:
    md_lines.append("## Rules (Legacy)")
    md_lines.append("")
    for rule in rules:
        name = rule.get("name", "Unnamed Rule")
        enabled = rule.get("enabled", False)
        script = rule.get("script", "")
        order = rule.get("order", "N/A")

        md_lines.append(f"### {name}")
        md_lines.append("")
        md_lines.append(f"- **Enabled:** {enabled}")
        md_lines.append(f"- **Order:** {order}")
        md_lines.append("")
        md_lines.append("**Script:**")
        md_lines.append("```javascript")
        md_lines.append(script if script else "// No script returned")
        md_lines.append("```")
        md_lines.append("")
else:
    md_lines.append("## Rules (Legacy)")
    md_lines.append("")
    md_lines.append("_No rules found — tenant likely uses Actions exclusively._")
    md_lines.append("")

output_path = "/private/tmp/claude-501/-Users-shristyj-CIAM-L1-SUPPORT-ASSISTANT-AGENT/684ce3cb-5933-4a8b-83a7-2fad57217dfa/scratchpad/auth0-workflow-scripts.md"
with open(output_path, "w") as f:
    f.write("\n".join(md_lines))

print(f"✅ Document written to: {output_path}")
print()
print("=" * 80)
print(f"SUMMARY: {len(detailed_actions)} action(s), {len(rules)} rule(s) documented")
print("=" * 80)
print()
print("Next steps:")
print("1. Review the generated markdown file")
print("2. Upload to S3: s3://ciam-agent4-kb-docs-786063285476-us-east-1/docs/")
print("3. Sync the Knowledge Base in AWS Console")
