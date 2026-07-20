# Redeploy Guide: Unit Test Refinement Agent

Use this whenever you change any code in this folder (`agent.py`, `generator.py`,
`prompts.py`, `github_input.py`, `validators.py`, `requirements.txt`, `Dockerfile`, etc.)
and need the change live on AgentCore.

## Fixed values (this agent)

```
AWS_ACCOUNT_ID=786063285476
REGION=ap-southeast-2
AGENT_RUNTIME_ID=unit_test_refine_agent-0ynGKdCbpl
AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-0ynGKdCbpl
EXECUTION_ROLE_ARN=arn:aws:iam::786063285476:role/unit-test-refine-agentcore-execution-role
ECR_REPO_URI=786063285476.dkr.ecr.ap-southeast-2.amazonaws.com/bedrock-agentcore-unit_test_refine_agent
CODEBUILD_PROJECT=bedrock-agentcore-unit_test_refine_agent-builder
GITHUB_PAT_SECRET_ARN=arn:aws:secretsmanager:ap-southeast-2:786063285476:secret:unit-test-gen-github-pat-qatgeG
```

## SSL note (do this first if any AWS/pip call fails with CERTIFICATE_VERIFY_FAILED)

This machine sits behind a corporate proxy. If you hit SSL errors:
```bash
export AWS_CA_BUNDLE=/Users/apanikar/.aws/combined-ca-bundle.pem
export REQUESTS_CA_BUNDLE=/Users/apanikar/.aws/combined-ca-bundle.pem
export SSL_CERT_FILE=/Users/apanikar/.aws/combined-ca-bundle.pem
```

---

## Method A (recommended): `agentcore` CLI — one command

The `bedrock-agentcore-starter-toolkit` is installed in this folder's `.venv`. It does
everything Method B does by hand: zip → S3 upload → CodeBuild build → ECR push →
`update-agent-runtime`, in one call. Verified working 2026-07-20.

### 1. Make your code change, then deploy

```bash
cd /Users/apanikar/Documents/GIS-SecEng-Intern/Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent

AGENTCORE_SUPPRESS_RECOMMENDATION=1 .venv/bin/agentcore deploy --auto-update-on-conflict \
  --env GITHUB_PAT_SECRET_ARN=arn:aws:secretsmanager:ap-southeast-2:786063285476:secret:unit-test-gen-github-pat-qatgeG
```

**`--auto-update-on-conflict` is required** — without it, `deploy` fails since the
agent already exists instead of updating it.

**`--env` is required every single time** — the CLI does not read back or preserve
environment variables already set on the runtime. Omit it and the redeploy silently
wipes `GITHUB_PAT_SECRET_ARN`, and every invoke fails with
`GITHUB_PAT_SECRET_ARN environment variable is not set`. If that happens, just rerun
`deploy` with `--env` included — it's a normal update, not a rollback situation.

Takes about 30-60s (CodeBuild build is small). Ends with a "Deployment Success" panel
showing the new ECR image tag and CodeBuild ID.

### 2. Check status

```bash
AGENTCORE_SUPPRESS_RECOMMENDATION=1 .venv/bin/agentcore status
```
Look for `Ready - Agent deployed and endpoint available`.

### 3. Test the deployed runtime end-to-end

```bash
.venv/bin/agentcore invoke '{"file_path":"NIC_SecEng_Task/vul_service.py","test_file_path":"Agentic_Unit_Test_Generator/tests/test_vul_service.py","repo":"netSkope/GIS-SecEng-Intern","ref":"<a commit SHA pushed to origin>"}'
```

Swap in whatever source/test file pair you want to check — must be a path that
actually exists at that ref **on GitHub** (the agent fetches via GitHub Contents API,
not your local disk). Expect `"status": "ok"` in the response. This call can take
1-2 minutes (real Bedrock model call) — if your shell auto-backgrounds it after 120s,
that's normal, just wait for it to finish.

### 4. Commit your code change

```bash
git add Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent/<changed files>
git commit -m "Describe the change"
```

`.bedrock_agentcore.yaml` gets auto-updated by `agentcore deploy` itself (new
CodeBuild role/project fields etc.) — commit that too if it changed.

---

## Method B (manual, no CLI): raw AWS CLI

Use this only if the toolkit isn't installed/working. Same underlying steps the CLI
automates.

### B1. Zip just this folder (not the whole repo)

The CodeBuild project's buildspec `cd`s into this folder before `docker build`, so the
zip must contain the path prefix `Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent/...`.
Run this from the **repo root**:

```bash
cd /Users/apanikar/Documents/GIS-SecEng-Intern

rm -f /tmp/source.zip
zip -r -q /tmp/source.zip \
  Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent \
  -x "*/__pycache__/*" \
  -x "*/.venv/*" \
  -x "*/deploy_env/*" \
  -x "*.pyc"
```

### B2. Upload the zip and trigger a build

```bash
aws s3 cp /tmp/source.zip \
  s3://bedrock-agentcore-codebuild-sources-786063285476-ap-southeast-2/unit_test_refine_agent/source.zip \
  --region ap-southeast-2

BUILD_ID=$(aws codebuild start-build \
  --project-name bedrock-agentcore-unit_test_refine_agent-builder \
  --region ap-southeast-2 \
  --query 'build.id' --output text)

echo "$BUILD_ID"
```

### B3. Wait for the build to finish

```bash
for i in {1..20}; do
  STATUS=$(aws codebuild batch-get-builds --ids "$BUILD_ID" \
    --region ap-southeast-2 --query 'builds[0].buildStatus' --output text)
  echo "check $i: $STATUS"
  [ "$STATUS" = "SUCCEEDED" ] && break
  [ "$STATUS" = "FAILED" ] && { echo "BUILD FAILED — check CodeBuild logs"; exit 1; }
  sleep 15
done
```

If it fails, check logs:
```bash
aws codebuild batch-get-builds --ids "$BUILD_ID" --region ap-southeast-2 \
  --query 'builds[0].logs.deepLink' --output text
```

### B4. Push the new image into the AgentCore runtime

The runtime pulls the image by tag (`:latest`), but a mutable tag alone doesn't force
a re-pull — you must call `update-agent-runtime` to bump the runtime version. This
call always needs the full set of options (role, network, protocol, env vars) —
anything you omit gets cleared, same gotcha as `--env` in Method A:

```bash
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id unit_test_refine_agent-0ynGKdCbpl \
  --agent-runtime-artifact '{"containerConfiguration":{"containerUri":"786063285476.dkr.ecr.ap-southeast-2.amazonaws.com/bedrock-agentcore-unit_test_refine_agent:latest"}}' \
  --role-arn arn:aws:iam::786063285476:role/unit-test-refine-agentcore-execution-role \
  --network-configuration '{"networkMode":"PUBLIC"}' \
  --protocol-configuration '{"serverProtocol":"HTTP"}' \
  --environment-variables '{"GITHUB_PAT_SECRET_ARN":"arn:aws:secretsmanager:ap-southeast-2:786063285476:secret:unit-test-gen-github-pat-qatgeG"}' \
  --region ap-southeast-2
```

### B5. Wait for it to come back READY

```bash
for i in {1..15}; do
  STATUS=$(aws bedrock-agentcore-control get-agent-runtime \
    --agent-runtime-id unit_test_refine_agent-0ynGKdCbpl \
    --region ap-southeast-2 --query 'status' --output text)
  echo "check $i: $STATUS"
  [ "$STATUS" = "READY" ] && break
  [ "$STATUS" = "UPDATE_FAILED" ] && { echo "UPDATE FAILED — check CloudWatch logs"; exit 1; }
  sleep 10
done
```

### B6. Test the deployed runtime end-to-end

```bash
export AGENT_RUNTIME_ARN="arn:aws:bedrock-agentcore:ap-southeast-2:786063285476:runtime/unit_test_refine_agent-0ynGKdCbpl"
export GITHUB_REPOSITORY="netSkope/GIS-SecEng-Intern"
export SOURCE_COMMIT_SHA="<a commit SHA that's pushed to origin>"

echo '[{"line": 5, "diff_hunk": "", "comment": "add a test for the injection path"}]' > /tmp/feedback.json

Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent/.venv/bin/python3 \
  Agentic_Unit_Test_Generator/scripts/refine_unit_test.py \
  Agentic_Unit_Test_Generator/tests/test_vul_service.py \
  /tmp/out_test_vul_service.py \
  /tmp/feedback.json
```

Expect `status: ok` and a written test file at the output path. If it errors with
`RuntimeError: bedrock-agentcore not installed`, the image build is missing the SDK —
check `requirements.txt` has `bedrock-agentcore` uncommented, then redo B1-B5.

### B7. Commit your code change

```bash
git add Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent/<changed files>
git commit -m "Describe the change"
```

`.bedrock_agentcore.yaml` doesn't need touching for a manual redeploy — `agent_id`
and `agent_arn` only change if you delete and recreate the runtime (a new
`agent-runtime-id`), not on an `update-agent-runtime` call.

---

## Rollback

If a redeploy breaks something and you need the previous image back, ECR keeps the
old digest even after `:latest` moves — find it and re-point the runtime:

```bash
aws ecr describe-images --repository-name bedrock-agentcore-unit_test_refine_agent \
  --region ap-southeast-2 --query 'imageDetails[].[imageDigest,imagePushedAt]' --output table

# then re-run B4 (or agentcore deploy with --image-tag pointing at an old build's tag)
# with containerUri pinned to that digest instead of :latest, e.g.:
# 786063285476.dkr.ecr.ap-southeast-2.amazonaws.com/bedrock-agentcore-unit_test_refine_agent@sha256:<digest>
```
