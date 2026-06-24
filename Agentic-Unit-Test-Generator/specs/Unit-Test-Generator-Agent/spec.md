| Key | Value |
| :--- | :--- |
| **spec_id** | SPEC-GHA-0001 |
| **capability** | unit-test-gen-agent |
| **status** | Draft |
| **owner** | Aryan Panikar |
| **reviewers** | Peer |
| **approver** | Rehman |
| **prd** | - |
| **jira_epic** | - |
| **version** | 0.0.1 |
| **created** | 2026-06-24 |
| **last_updated** | 2026-06-24 |

# spec.md — Unit Test Generator Agent

> This is the **executable contract**. Code, evals, and PR review trace back to
> this file. Acceptance criteria map 1:1 to eval cases under
> `evals/unit-test-gen-agent/cases/`. Posture/loop-prevention invariants
> (AC-5, AC-6, AC-9) are **gating in CI**: a regression fails the PR.

---

## 1. Summary

The Unit Test Generation Agent is a GitHub Actions–native, event-driven
pipeline that automatically generates security-focused unit tests for every
human-authored Pull Request targeting the `main` branch. On PR open, the agent
reads the diff/patch context of changed files, dynamically detects the
programming language(s) of those files, and invokes **AWS Bedrock
(Claude 3.5 Sonnet)** via a hardened, security-focused system prompt to generate
high-coverage unit tests in the language's native testing framework (e.g.,
`pytest`, `JUnit 5`, `Jest`). The generated test files are committed and pushed
directly back to the developer's source feature branch, updating the open PR
workspace in-place.

Test **execution** is fully decoupled from test **generation** into a separate
`test-runner.yml` workflow. This architectural separation enforces the
infinite-loop invariant: the generation workflow halts immediately when the
commit actor is the GitHub Actions bot, preventing recursive self-triggering.

Authentication to AWS Bedrock is **keyless only** — achieved via OpenID Connect
(OIDC) identity federation. Static, long-lived AWS access keys or GitHub Secrets
holding AWS credentials are explicitly prohibited and constitute a release
blocker.

Phase 1 is generate-and-commit-only. No auto-merge, no suppression of findings,
and no mutation of the developer's application code is within scope until a
separate ADR introduces those flows.

---

## 2. Goals / Non-Goals

### Goals

- Trigger automatically on every human-authored PR targeting `main`.
- Detect the programming language of each changed file and select the matching
  native test framework.
- Generate security-focused unit tests (boundary values, malicious inputs, type
  confusion, exception safety) via AWS Bedrock (Claude 3.5 Sonnet).
- Commit and push generated test files back to the PR's feature branch without
  human intervention.
- Prevent infinite trigger loops by halting immediately when `github.actor` is
  `github-actions[bot]`.
- Route Dependabot PRs (dependency-only bumps) directly to the test runner,
  bypassing generation entirely.
- Authenticate to AWS Bedrock using OIDC federation only — no static keys.
- Emit structured result objects (conforming to `core/results/schema.py`) for
  every generation run, whether successful or failed.
- Validate all result objects against the schema in CI (gating invariant).

### Non-goals

- Mutation or refactoring of the developer's application source code.
- Auto-merging PRs (deferred — pending a separate ADR and human approval gate).
- Generation of integration, end-to-end, or load tests (deferred).
- Coverage reporting, badge generation, or test-trend dashboards (deferred).
- Support for languages beyond Python, Java, and TypeScript in Phase 1
  (additional languages added via spec amendment, not ad-hoc).
- Secrets scanning, SAST, or dependency vulnerability analysis (owned by sibling
  agents/workflows).

---

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| PR trigger event | `github.event` (`pull_request`) | Types: `opened`, `reopened`. The generation workflow does **not** trigger on `synchronize` — that is the test runner's domain. |
| Actor identity | `github.actor` | Used for the bot-bypass invariant. If `github.actor == 'github-actions[bot]'`, the generation step is skipped unconditionally. |
| PR author association | `github.event.pull_request.user.login` | Dependabot fast-track: if login matches `dependabot[bot]`, skip generation and route directly to test runner. |
| Diff / patch context | `git diff origin/main...HEAD` | Raw unified diff of changed files relative to `main`. Fed verbatim to the Bedrock prompt (truncated at 32 000 tokens). |
| Changed file list | `git diff --name-only origin/main...HEAD` | Used for language detection; paths relative to repo root. |
| Feature branch ref | `github.head_ref` | Target branch for the generated-test commit push. |
| AWS region | Environment variable `AWS_REGION` (default `us-east-1`) | Resolved at workflow bootstrap; not a secret. |
| Bedrock model ID | Workflow env `BEDROCK_MODEL_ID` (default `anthropic.claude-3-5-sonnet-20241022-v2:0`) | Pinned model ID; changes require a spec amendment and PR. |
| OIDC role ARN | Workflow env `AWS_ROLE_ARN` | The IAM role federated to via OIDC. No key material. |
| Repo write token | `secrets.GITHUB_TOKEN` (built-in) | Scoped to `contents: write`, `pull-requests: read`. Used for the git push back to the feature branch. No PAT or external secret. |

The agent is **stateless** between runs. No persistent database or cache is
required in Phase 1.

---

## 4. Permitted Tools / Authorization Boundary

The agent's IAM execution role (assumed via OIDC) **MAY** perform only the
actions in this table. The CDK/Terraform stack in `infra/aws/unit-test-gen-agent/`
MUST instantiate this exact policy shape; no `*` action wildcards beyond the
explicit list below are permitted.

| Service | Action | Resource scope |
| :--- | :--- | :--- |
| Bedrock | `bedrock:InvokeModel` | Scoped to `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-*` only |
| STS | `sts:AssumeRoleWithWebIdentity` | The agent's own OIDC-federated role ARN only |
| CloudWatch Logs | `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` | `arn:aws:logs:*:*:log-group:/unit-test-gen-agent/*` only |

The GitHub Actions runner's **`GITHUB_TOKEN`** permissions are set at the
workflow level and MUST be scoped as follows. Any permission not listed is
implicitly denied by GitHub's token model.

| `GITHUB_TOKEN` Permission | Level | Purpose |
| :--- | :--- | :--- |
| `contents` | `write` | Commit and push generated test files to the feature branch |
| `pull-requests` | `read` | Read PR metadata (actor, head ref, labels) |
| `id-token` | `write` | Obtain the OIDC JWT for AWS federation |
| All others | `none` (implicit deny) | Defense-in-depth; no package, deployment, or admin rights |

Any tool implementation that calls an AWS API not in the Bedrock/STS/CWL table
above is a **defect and a release blocker**.

---

## 5. Explicit Denies (Phase 1 Invariants)

The IAM execution role MUST carry an explicit `Deny` statement covering the
following actions with `Resource: "*"`. These denies are **gating posture
invariants** — CI fails the PR if they are missing or weakened.

| Denied Action | Reason |
| :--- | :--- |
| `iam:*` | Agent must never read or mutate IAM configuration. |
| `s3:*` | No S3 access; all state is in-memory or GitHub-hosted. |
| `ec2:*` | Agent performs no network or compute operations. |
| `organizations:*` | Agent has no visibility into AWS Org structure. |
| `bedrock:CreateAgent`, `bedrock:DeleteAgent` | Agent may invoke models; it may not author or destroy agents. |
| `bedrock:PutModelInvocationLoggingConfiguration` | Agent may not alter audit/logging configuration of Bedrock. |
| `sts:AssumeRole` (cross-account) | Agent may only assume its own OIDC role; no cross-account hop. |
| `secretsmanager:GetSecretValue` | Keyless-only invariant: agent must never retrieve static credentials. |
| `ssm:GetParameter` | Same keyless-only rationale as above. |

**Workflow-level denies (GitHub Actions):**

| Prohibited Pattern | Reason |
| :--- | :--- |
| `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in any `env:` or `with:` block | Keyless-only invariant — static credentials are a release blocker. |
| `permissions: write-all` at job or workflow level | Least-privilege invariant — scoped permissions only. |
| `if:` condition omitted on the generation step | Bot-bypass invariant — the loop-prevention guard must always be present. |
| Pushing to `main` directly | Agent MUST commit only to `github.head_ref` (the feature branch). |

Defense in depth: in addition to IAM denies, the agent's Python orchestrator
(`environments/github-actions/security_test_gen/orchestrator.py`) MUST maintain
an allow-list of permitted Bedrock API calls. Any invocation outside the
allow-list raises `PostureViolationError` before the boto3 call is issued, and
the violation is itself recorded as a result of category `posture-violation`
(severity `CRITICAL`).

---

## 6. Behavior

A generation run proceeds in the following deterministic steps. Step numbers
correspond to the eval cases in §9.

### 6.1 Generation Workflow (`test-gen.yml`)

```
Trigger: pull_request → [opened, reopened] targeting main
```

**Step 1 — Bot-bypass gate (GATING invariant).**
Evaluate `github.actor`. If the actor is `github-actions[bot]`, exit the job
immediately with `conclusion: skipped`. No Bedrock call is made, no commit is
attempted. This is the primary loop-prevention mechanism.

**Step 2 — Dependabot fast-track gate.**
If `github.event.pull_request.user.login` matches `dependabot[bot]`, exit the
generation job with `conclusion: skipped`. The test runner workflow handles the
PR independently; no AI generation is needed for dependency-only bumps.

**Step 3 — OIDC authentication.**
Use `aws-actions/configure-aws-credentials` with `role-to-assume: $AWS_ROLE_ARN`
and `role-session-name: unit-test-gen-${{ github.run_id }}`. The step MUST
NOT reference `aws-access-key-id` or `aws-secret-access-key` in its `with:`
block. Failure to obtain credentials aborts the run with `status: failed`.

**Step 4 — Diff extraction.**
Execute `git fetch origin main` then `git diff origin/main...HEAD` to produce
the unified diff. Also collect `git diff --name-only origin/main...HEAD` for the
changed file list. Truncate the combined diff payload to **32 000 tokens** if
necessary (longest-file-first removal strategy); record `evidence.truncated: true`
when truncation occurs.

**Step 5 — Language detection.**
Inspect each changed file's extension:

| Extension(s) | Detected language | Native framework |
| :--- | :--- | :--- |
| `.py` | Python | `pytest` |
| `.java` | Java | `JUnit 5` (+ Mockito) |
| `.ts`, `.tsx` | TypeScript | `Jest` (+ ts-jest) |

If a PR touches files from multiple languages, the agent runs one Bedrock
invocation per language group, each with a language-specific system prompt.
If a file extension is unrecognized, it is skipped and recorded in
`evidence.skipped_files`.

**Step 6 — Bedrock invocation.**
Invoke `bedrock:InvokeModel` with the following payload structure:

```json
{
  "modelId": "<BEDROCK_MODEL_ID>",
  "contentType": "application/json",
  "accept": "application/json",
  "body": {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 8192,
    "system": "<security-focused system prompt — see §6.3>",
    "messages": [
      {
        "role": "user",
        "content": "<diff payload — see §6.4>"
      }
    ]
  }
}
```

Retry policy: exponential backoff with jitter, max 4 retries, initial delay
2 s, cap 30 s. After max retries, the run concludes with `status: partial` and
`evidence.partial_reason: "bedrock_throttled"`.

**Step 7 — Test file extraction.**
Parse the model's response to extract fenced code blocks (` ```python `,
` ```java `, ` ```typescript `). Each extracted block is written to a
deterministic file path:

```
tests/security/auto-generated/<language>/<source_file_stem>_sec_test.<ext>
```

Example: `src/auth/validator.py` → `tests/security/auto-generated/python/validator_sec_test.py`.

If the model returns no code blocks, the step records
`evidence.generation_result: "no_code_blocks_returned"` and exits with
`status: partial`.

**Step 8 — Commit and push.**
Configure git with identity `github-actions[bot] <github-actions[bot]@users.noreply.github.com>`.
Stage all files under `tests/security/auto-generated/`. Commit with message:

```
chore(security-tests): auto-generate security unit tests [skip ci]

Generated by SPEC-GHA-0001 unit-test-gen-agent
Run: ${{ github.run_id }} | PR: #${{ github.event.pull_request.number }}
```

> **Note:** The `[skip ci]` token in the commit message is a secondary
> loop-prevention layer (belt-and-suspenders). The primary guard is Step 1
> (`github.actor` check), which is the gating invariant. `[skip ci]` alone is
> **not** sufficient.

Push to `${{ github.head_ref }}` using the scoped `GITHUB_TOKEN`. On push
failure (e.g., branch protection conflict), emit a result with
`status: failed`, `evidence.error_class: "push_rejected"`, and surface the
error as a PR comment via the GitHub API (`pull-requests: write` permission
would be needed — see OQ-2).

**Step 9 — Emit result object.**
Write one `GenerationResult` (§7) per language group to stdout as
newline-delimited JSON. The CI step captures this output and uploads it as a
workflow artifact (`unit-test-gen-results-<run_id>.jsonl`).

---

### 6.2 Test Runner Workflow (`test-runner.yml`)

```
Trigger: pull_request → [opened, synchronize, reopened] targeting main
```

This workflow is fully decoupled from `test-gen.yml`. It executes after every
PR event (including the bot commit from Step 8 above, which fires a `synchronize`
event). The runner:

1. Checks out the PR's head commit (which now includes the AI-generated tests).
2. Installs dependencies for each detected language.
3. Runs the native test framework:
   - Python: `pytest tests/ -v --tb=short`
   - Java: `mvn test` or `./gradlew test`
   - TypeScript: `npx jest --passWithNoTests`
4. Publishes a test summary to the PR using the native GitHub summary API.
5. Gates the PR status check: if any test fails, `test-runner` posts a failing
   required status check, blocking merge.

The test runner does **not** invoke AWS Bedrock, read diffs, or commit any files.
It is a pure executor.

**Dependabot path:** When `github.actor == 'dependabot[bot]'`, the test runner
executes the full test suite against the upgraded dependencies. If all tests
pass, the PR may be auto-merged by a separate merge-bot configuration (out of
scope for this spec). If tests fail, the PR blocks and a human must review the
breaking change.

---

### 6.3 Security-Focused System Prompt (Normative)

The system prompt passed to Bedrock MUST contain the following instructions
verbatim (language-specific sections are parameterized via `{LANGUAGE}` and
`{FRAMEWORK}`):

```
You are an expert AppSec engineer and senior {LANGUAGE} developer specializing
in adversarial test design. Your task is to generate a comprehensive,
security-focused unit test file in {LANGUAGE} using the {FRAMEWORK} framework
for the code changes shown in the provided diff.

REQUIRED TEST CATEGORIES — you MUST include tests for each:
1. BOUNDARY VALUE CONDITIONS: test minimum, maximum, zero, negative, and
   off-by-one values for every numeric or length-bounded input.
2. MALICIOUS AND UNEXPECTED INPUTS: SQL injection fragments, XSS payloads,
   path traversal strings (../../../etc/passwd), null bytes, oversized strings
   (>= 10 000 characters), Unicode edge cases (RTL markers, null code points),
   and shell metacharacters.
3. TYPE CONFUSION: pass values of the wrong type where typed values are expected
   (e.g., string where int expected, None/null, boolean coerced to numeric).
4. STRUCTURAL EDGE CASES: empty collections, single-element collections,
   deeply nested structures, circular reference candidates, and malformed
   serialized payloads (invalid JSON, truncated base64).
5. EXCEPTION SAFETY: confirm that functions raise the correct typed exception
   (not a generic catch-all) for invalid inputs and that resources are not
   leaked on exception paths.
6. AUTHENTICATION AND AUTHORIZATION INVARIANTS (if applicable): confirm that
   unauthenticated callers, callers with insufficient scope, and callers with
   expired tokens are rejected with the correct status code / exception type.

OUTPUT FORMAT:
- Return ONLY a single fenced code block in {LANGUAGE}.
- Do not include explanatory prose outside the code block.
- Include a module-level docstring citing SPEC-GHA-0001.
- Every test function name must begin with test_security_ or test_edge_.
- All test data must be defined as constants or parametrize decorators —
  never inline magic values.
```

---

### 6.4 User-Turn Diff Payload Format

```
The following is a unified diff of changed files in this pull request.
Repository: {REPO_FULL_NAME}
PR number: {PR_NUMBER}
Language group: {LANGUAGE}

<diff>
{TRUNCATED_DIFF_CONTENT}
</diff>

Generate the security-focused {FRAMEWORK} test file now.
```

---

### 6.5 Determinism

For identical diff inputs the structured `GenerationResult` output is
**byte-stable** except for `run_id` and `generated_at`. Determinism of the
Bedrock response is best-effort (temperature=0 is set in the API call); the
result schema is the stability contract, not the LLM text. Verified in eval AC-8.

---

### 6.6 Redaction

The agent never writes raw diff content, API keys, or AWS account IDs to PR
comments, workflow summaries, or artifact payloads. Workflow logs are scoped by
GitHub's built-in secret masking. Evidence fields carry only:

- File paths (relative, no absolute paths).
- Language detection results.
- Truncation status and token counts.
- Bedrock response metadata (input/output token counts, stop reason).
- SHA-256 of the generated test file content (for change detection).

---

## 7. Outputs / Result Schema

Every generation run emits one `GenerationResult` per language group, conforming
to `core/results/schema.py`. The shape is:

```python
class GenerationResult(BaseModel):
    schema_version: Literal["1.0"]
    spec_id: str                          # "SPEC-ABC-0001"
    agent: Literal["unit-test-gen-agent"]
    run_id: str                           # github.run_id (string)
    generated_at: datetime                # UTC, isoformat
    repo: str                             # "org/repo"
    pr_number: int
    language: Literal["python", "java", "typescript"]
    framework: Literal["pytest", "junit5", "jest"]
    status: Literal["ok", "partial", "failed", "skipped"]
    output_paths: list[str]               # relative paths of committed test files
    evidence: dict[str, Any]              # see below
    partial: bool = False                 # true on partial-failure runs

class Evidence(TypedDict, total=False):
    truncated: bool                       # diff was truncated to fit token window
    truncated_files: list[str]            # files removed during truncation
    skipped_files: list[str]             # unrecognized extensions
    generation_result: str               # "ok" | "no_code_blocks_returned"
    partial_reason: str                  # "bedrock_throttled" | "push_rejected"
    error_class: str                     # exception class name on hard failure
    bedrock_input_tokens: int
    bedrock_output_tokens: int
    bedrock_stop_reason: str             # "end_turn" | "max_tokens" | "stop_sequence"
    output_sha256: dict[str, str]        # {relative_path: sha256_hex}
```

Every `GenerationResult` MUST validate against `core/results/schema.py` (Pydantic
strict mode). Schema validation failure is itself a gating CI invariant (AC-9).

---

## 8. Failure Handling

| Failure mode | Behavior |
| :--- | :--- |
| **OIDC credential failure** (e.g., role ARN misconfigured, audience mismatch) | Run exits with `status: failed`, `evidence.error_class: "OIDCFederationError"`. Workflow posts a failed required status check. Human must investigate IAM/OIDC trust policy. |
| **Bedrock throttling** (HTTP 429 / `ThrottlingException`) | Exponential backoff, max 4 retries. After exhaustion: `status: partial`, `evidence.partial_reason: "bedrock_throttled"`. Partial result emitted; generation may be incomplete. |
| **Bedrock model unavailable** (HTTP 5xx) | Same retry policy as throttling. After exhaustion: `status: failed`. |
| **No code blocks in response** | `status: partial`, `evidence.generation_result: "no_code_blocks_returned"`. No commit is made. Workflow posts an informational PR comment advising manual test authorship. |
| **Git push rejected** (branch protection, merge conflict) | `status: failed`, `evidence.error_class: "push_rejected"`. No retry. Workflow surfaces the error; human resolves conflict and re-opens or re-pushes. |
| **Unrecognized language** (all changed files have unknown extensions) | `status: skipped`, `evidence.skipped_files: [...]`. No Bedrock call is made. The test runner still executes on any pre-existing tests. |
| **Diff exceeds 32 000 tokens** | Truncation applied (longest-file-first). `evidence.truncated: true`, `evidence.truncated_files: [...]`. Run continues with truncated diff. |
| **Posture violation (tripwire)** | `PostureViolationError` raised before the SDK call. `status: failed`. Workflow halts immediately. A `posture-violation` result (`CRITICAL`) is emitted. This is a release-blocker defect. |
| **Schema validation failure** | `GenerationResult` fails Pydantic strict-mode validation. `status: failed`. This is a gating CI failure — the PR cannot merge until resolved. |

Partial failures do **not** block the test runner from executing. The runner
workflow's `synchronize` trigger fires on any push to the branch, including
partial-commit scenarios.

---

## 9. Acceptance Criteria (Given/When/Then)

Each AC maps 1:1 to an eval case at `evals/unit-test-gen-agent/cases/ac-N.yaml`.
ACs marked **GATING** fail the PR in CI if they regress.

---

### AC-1 — Generation triggered on human PR open

**Given** a human developer opens a PR targeting `main` with changes to Python
files,\
**When** the `test-gen.yml` workflow runs,\
**Then** the generation job executes to completion, a `GenerationResult` with
`status: ok`, `language: "python"`, and `framework: "pytest"` is emitted, and
at least one file matching `tests/security/auto-generated/python/*_sec_test.py`
is committed to the feature branch.

---

### AC-2 — Bot-bypass gate prevents infinite loop **(GATING — loop invariant)**

**Given** the `test-gen.yml` workflow is triggered by a `push` event whose
`github.actor` is `github-actions[bot]` (i.e., the agent just pushed generated
tests back to the branch, firing a `synchronize` which could re-trigger
generation),\
**When** the workflow evaluates the bot-bypass gate at Step 1,\
**Then** the generation job exits immediately with `conclusion: skipped`, no
Bedrock API call is made, no commit is attempted, and the resulting
`GenerationResult` carries `status: "skipped"`. **Gating in CI.**

---

### AC-3 — Dependabot PR fast-tracked to test runner

**Given** a PR is opened by `dependabot[bot]` to bump a dependency version,\
**When** the `test-gen.yml` workflow evaluates the Dependabot gate at Step 2,\
**Then** the generation job exits with `conclusion: skipped`, no Bedrock call
is made, and the `test-runner.yml` workflow executes independently against the
upgraded dependencies.

---

### AC-4 — Keyless OIDC authentication enforced; static keys rejected

**Given** the `test-gen.yml` workflow is inspected for the presence of
`aws-access-key-id` or `aws-secret-access-key` in any `env:` or `with:` block
(checked by a CI lint step),\
**When** the lint step runs on every PR,\
**Then** the lint step fails the PR if any static key reference is detected.
Conversely, when `aws-actions/configure-aws-credentials` is configured with
`role-to-assume` only, the lint step passes and the OIDC handshake succeeds.

---

### AC-5 — Security test categories present in generated output

**Given** a PR containing a Python function that accepts a user-supplied string
argument,\
**When** the agent generates the security test file,\
**Then** the generated test file contains at least one test function exercising
each of the following: a boundary value input, a malicious input (e.g., SQL
injection fragment or path traversal), a type confusion input (e.g., `None`),
and an oversized string (>= 10 000 characters), and every such function name
begins with `test_security_` or `test_edge_`.

---

### AC-6 — Multi-language PR produces per-language test files

**Given** a PR modifying both `src/auth/validator.py` (Python) and
`src/api/client.ts` (TypeScript),\
**When** the agent runs Steps 4–7,\
**Then** two separate Bedrock invocations are made (one per language group), and
two `GenerationResult` objects are emitted with `language: "python"` and
`language: "typescript"` respectively, each with a committed test file in the
correct sub-directory.

---

### AC-7 — Partial failure on Bedrock throttle still emits result

**Given** a simulated Bedrock `ThrottlingException` that persists through all 4
retry attempts,\
**When** the agent exhausts retries,\
**Then** a `GenerationResult` is emitted with `status: "partial"`,
`partial: true`, `evidence.partial_reason: "bedrock_throttled"`, and no test
file is committed to the branch. The test runner continues to execute against
any pre-existing tests.

---

### AC-8 — Unrecognized file type results in graceful skip

**Given** a PR that modifies only `.sol` (Solidity) files,\
**When** the agent runs language detection at Step 5,\
**Then** all changed files are recorded in `evidence.skipped_files`, a
`GenerationResult` is emitted with `status: "skipped"`, and no Bedrock call
is made.

---

### AC-9 — Schema conformance **(GATING — schema invariant)**

**Given** any run that emits one or more `GenerationResult` objects,\
**When** each object is validated against `core/results/schema.py` (Pydantic
strict mode),\
**Then** every object passes validation. Any validation failure fails the CI
gate and blocks PR merge. **Gating in CI.**

---

### AC-10 — Test runner executes after bot commit

**Given** the generation agent has pushed a new commit of generated tests to the
feature branch (firing a `synchronize` PR event),\
**When** the `test-runner.yml` workflow evaluates its trigger,\
**Then** the test runner executes the full test suite against the updated branch
(including the generated tests), posts a status check to the PR, and the
generation job does **not** re-execute (verified by AC-2).

---

### AC-11 — Posture violation raises `PostureViolationError` before SDK call **(GATING — posture invariant)**

**Given** a malformed orchestrator invocation that attempts to call an AWS API
outside the permitted allow-list (e.g., `s3:GetObject`),\
**When** the orchestrator's allow-list guard evaluates the call,\
**Then** `PostureViolationError` is raised before the boto3 call is issued, a
`GenerationResult` with `status: "failed"` and `evidence.error_class:
"PostureViolationError"` is emitted, and no AWS API call outside the allow-list
reaches the wire. **Gating in CI.**

---

## 10. Eval Mapping Table

| AC | Eval case file | Type | Gating |
| :--- | :--- | :--- | :--- |
| AC-1 | `evals/unit-test-gen-agent/cases/ac-1.yaml` | structured-assertion | no |
| AC-2 | `evals/unit-test-gen-agent/cases/ac-2.yaml` | loop-invariant | **yes** |
| AC-3 | `evals/unit-test-gen-agent/cases/ac-3.yaml` | structured-assertion | no |
| AC-4 | `evals/unit-test-gen-agent/cases/ac-4.yaml` | lint-invariant | **yes** |
| AC-5 | `evals/unit-test-gen-agent/cases/ac-5.yaml` | structured-assertion | no |
| AC-6 | `evals/unit-test-gen-agent/cases/ac-6.yaml` | structured-assertion | no |
| AC-7 | `evals/unit-test-gen-agent/cases/ac-7.yaml` | failure-mode | no |
| AC-8 | `evals/unit-test-gen-agent/cases/ac-8.yaml` | structured-assertion | no |
| AC-9 | `evals/unit-test-gen-agent/cases/ac-9.yaml` | schema-invariant | **yes** |
| AC-10 | `evals/unit-test-gen-agent/cases/ac-10.yaml` | integration-assertion | no |
| AC-11 | `evals/unit-test-gen-agent/cases/ac-11.yaml` | posture-invariant | **yes** |

---

## 11. Repository Layout (Normative)

```
.
├── .github/
│   └── workflows/
│       ├── test-gen.yml          # Generation workflow (this agent)
│       └── test-runner.yml       # Decoupled execution workflow
├── specs/
│   └── unit-test-gen-agent/
│       ├── spec.md               # ← THIS FILE (executable contract)
│       ├── prd.md                # Product requirements (thinking lane)
│       └── tasks.md              # Implementation task breakdown
├── prompts/
│   └── unit-test-gen-agent/
│       └── system_prompt.md      # Versioned Bedrock system prompt (§6.3)
├── core/
│   └── results/
│       └── schema.py             # GenerationResult Pydantic model
├── environments/
│   └── github-actions/
│       └── unit_test_gen/
│           ├── orchestrator.py   # Main agent logic (Steps 1–9)
│           ├── lang_detect.py    # Language/framework detection
│           ├── bedrock_client.py # Bedrock invocation + retry
│           └── git_ops.py        # Commit/push operations
├── infra/
│   └── aws/
│       └── unit-test-gen-agent/
│           ├── iam_role.tf       # OIDC trust policy + inline deny
│           └── main.tf
├── evals/
│   └── unit-test-gen-agent/
│       └── cases/
│           ├── ac-1.yaml … ac-11.yaml
│           └── fixtures/         # Synthetic diffs and mock Bedrock responses
└── docs/
    ├── adr/
    │   └── 0001-oidc-keyless-auth.md
    └── diagrams/
        └── test-gen-flow.mmd     # Mermaid sequence diagram
```

---

## 12. Open Questions

**OQ-1.** Should the generation workflow also trigger on `reopened` when the
reopener is a human but the last commit was from the bot? Current behavior: yes,
because the actor check is on `github.actor` (the reopener), not the last
committer. Confirm with Architecture before Phase 1 ships.

**OQ-2.** Should the agent post a PR comment summarizing generated tests (e.g.,
"Generated 14 security tests across 3 files")? This requires `pull-requests: write`
on `GITHUB_TOKEN`. Currently deferred; if added, requires a spec amendment and
the comment content must be reviewed for redaction compliance (§6.6).

**OQ-3.** Token window management strategy when diffs exceed 32 000 tokens:
current strategy is longest-file-first removal. Alternative is proportional
truncation. Decision pending benchmarking against real PR sizes in the target
repos. Defaulting to longest-file-first for Phase 1.

**OQ-4.** Should generated test files be committed to the feature branch (current
design) or opened as a separate PR targeting the feature branch? Separate PR adds
review surface but increases workflow complexity. Current design (direct commit)
is simpler and consistent with the `[skip ci]` + actor-check loop prevention.
Revisit if teams request an explicit review gate on generated tests.

**OQ-5.** Model pinning strategy: `claude-3-5-sonnet-20241022-v2:0` is pinned in
the workflow env. When a newer model version is available, the update requires a
spec amendment (model ID change in §3), a re-run of all AC evals, and a PR
approved by the spec owner. No ad-hoc model swaps.