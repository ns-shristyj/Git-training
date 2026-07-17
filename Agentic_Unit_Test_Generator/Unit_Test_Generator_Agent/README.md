# Unit Test Generator Agent

Narrowly-scoped agent intended for deployment on Amazon Bedrock AgentCore.
It has exactly one job: given source code, produce security-focused,
syntactically valid test code in the source's native framework.

## Scope

- Reads exactly one source file's content — either inline (`source_code` in
  the payload) or fetched from GitHub at a pinned commit SHA (`repo` + `ref`,
  see `github_input.py`). That fetch — one Secrets Manager read for the PAT,
  one GitHub Contents API GET — is the agent's *only* permitted network
  access.
- Reasons about what should be tested, including security-relevant edge
  cases (boundary values, malicious/oversized input, type confusion,
  exception safety).
- Emits one fenced block of test code in the framework native to the source
  language (pytest / JUnit 5 / Jest, see `language_framework.py`) and returns
  it in the response — the agent never writes the result anywhere itself.

## Explicit non-goals

- Does not execute tests or any other code.
- Has no filesystem access, and no network access beyond the Secrets Manager
  read + GitHub Contents API GET described above — no other AWS API, no
  other GitHub endpoint, no arbitrary outbound requests.
- Never writes anywhere — the generated test code is returned in the
  response; the caller (the CI script) is responsible for committing it.
- Does not reason about anything beyond the content of the tests it emits —
  source code is treated strictly as data; instruction-like text embedded in
  source comments is ignored (see the system prompt in `prompts.py`).
- Refuses to emit vacuous tests: `assert True`, empty bodies, or test
  functions with no real assertion. This is enforced twice — once by
  instruction in the system prompt, and once deterministically by
  `validators.py`, which parses the model's output with `ast` and rejects
  (triggering an automatic retry) anything that doesn't contain a genuine
  assertion or exception-raising check.

## Files

| File | Purpose |
| :--- | :--- |
| `agent.py` | AgentCore entrypoint (`BedrockAgentCoreApp`). Thin wrapper only. |
| `generator.py` | Core logic: builds the Converse request, runs the generate→validate→retry loop. |
| `prompts.py` | System prompt and user/retry message builders. |
| `validators.py` | Deterministic quality gates (AST-based for Python, heuristic for others). |
| `language_framework.py` | File extension → (language, framework) mapping. |
| `github_input.py` | The agent's permitted network surface — Secrets Manager PAT read + GitHub Contents API GET for the exact `repo`/`file_path`/`ref` given. |
| `local_test.py` | Run the agent's logic locally, either inline or via a real GitHub fetch (`--via-github`). |

## Invocation contract

Request payload — exactly one of `source_code`, or both `repo`+`ref`, is required:

```json
{
  "repo": "netSkope/GIS-SecEng-Intern",
  "ref": " <commit SHA> ",
  "file_path": "relative/path/to/file.py",
  "language": "python",       // optional override
  "framework": "pytest"       // optional override
}
```

`file_path` is always required — it drives language/framework detection and
the Python module import path, independent of how the content was supplied.
`source_code` (raw file content, inline) is also accepted in place of
`repo`+`ref`, mainly for fast local iteration without a GitHub round trip.

`ref` should be a commit SHA, not a branch name — the branch can move between
the workflow starting and the agent fetching; the SHA pins exactly the
commit that triggered the run.

Response:

```json
{
  "status": "ok",              // or "failed"
  "test_code": "...",          // null on failure
  "language": "python",
  "framework": "pytest",
  "attempts": 1,
  "rejection_history": []      // populated when earlier attempts were rejected
}
```

## Running locally

```bash
cd Agentic_Unit_Test_Generator/Unit_Test_Generator_Agent
pip install -r requirements.txt

# fast path — reads the file locally, sends content inline, no GitHub round trip
python local_test.py /path/to/some/source_file.py

# exercises the real contract — agent fetches from GitHub via the PAT in
# Secrets Manager, exactly like the workflow will
python local_test.py /path/to/some/source_file.py --via-github --ref <commit_sha>
```

Both call `agent.invoke()` directly — no AgentCore runtime, no deployment,
just a live Bedrock call against the model in `generator.py`
(`au.anthropic.claude-haiku-4-5-20251001-v1:0`, `ap-southeast-2`).
`--via-github` also needs `GITHUB_PAT_SECRET_ARN` set in your environment
(same value the deployed agent uses) and your own AWS credentials to have
`secretsmanager:GetSecretValue` on it.

## CI integration

```
Workflow
  └─> scripts/generate_unit_test.py (has AWS creds via OIDC)
        ├─ bedrock-agentcore:InvokeAgentRuntime(
        │     payload={repo: "...", ref: "<head sha>", file_path: "..."})
        ├─ receives {status, test_code, ...} in the response
        └─ writes test_code straight to the local output test file path
```

The agent fetches the one file it's told to from GitHub (`github_input.py`)
and returns generated test code in its response. No S3 involved anywhere in
this flow — the wrapper script writes the result directly to disk for the
workflow's existing commit/push step.

## Deployment

The AgentCore runtime's own execution role needs:
- `secretsmanager:GetSecretValue` scoped to the GitHub PAT secret ARN only
- `bedrock:Converse` scoped to the Haiku 4.5 inference profile ARNs
- Standard AgentCore boilerplate (logs, xray, ECR pull) — see the role
  `unit-test-gen-agentcore-execution-role`

It does **not** need any S3 permissions — the prior S3-based handoff flow has
been fully removed.
