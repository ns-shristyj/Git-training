| spec_id | SPEC-ABC-0001 |
| capability | unit-test-generator-agent |
| status | Draft |
| owner | Aryan Panikar |
| reviewers | Peer |
| approver | Rehman |
| prd | - |
| jira_epic | - |
| version | 0.0.1 |
| created | 2026-06-23 |
| last_updated | 2026-06-23 |


# spec.md --- Unit Test Generation Agent

> This is the **executable contract**. The GitHub Actions automation loop,
> AI prompt context engineering, and pre-merge validation gates trace back
> directly to this file. Posture safety checks (AC-6, AC-7) are **gating in CI**:
> any breakdown or infinite loop regression fails the build.

## 1. Summary

The Unit Test Generation Agent is a development lifecycle automation component designed to drastically reduce security regression rates across multi-language codebases. When a developer opens a Pull Request (PR) targeting `main`, a dedicated GitHub Actions workflow intercepts the modified application code. The agent dynamically detects the programming language of the modified files and passes the diff context securely to AWS Bedrock (Claude 3.5 Sonnet) using a specialized, security-focused AppSec prompt context.

The agent generates high-coverage unit test files matching **the exact programming language and native testing framework** of the modified code (e.g., `pytest` for Python, `JUnit` for Java, `Jest/Mocha` for TypeScript/JavaScript, etc.). These generated tests are automatically pushed directly back into the developer's source branch. A completely isolated, decoupled secondary workflow then handles test execution, establishing an automated, green-to-merge verification loop before human review begins.

## 2. Goals / Non-Goals

### Goals
- Automatically catch file modifications on `pull_request` events and extract changed code.
- **Dynamically detect the source language** of modified files to dictate the target test framework format.
- Leverage AWS Bedrock via secure OpenID Connect (OIDC) authentication to generate targeted unit test files in the matching programming language.
- Inject strict AppSec testing contexts (boundary conditions, malicious inputs, type confusion checks).
- Push generated test code natively into the developer's remote feature branch to populate the PR workspace.
- Isolate the test generation engine from the test execution engine to explicitly prevent infinite CI/CD runner execution loops.

### Non-goals
- Modifying, refactoring, or cleaning up the developer's actual application source code.
- Executing or compiling the generated test suites inside the generation workflow runner.
- Managing production deployments or interacting with resources outside the repository and AWS Bedrock runtime scoped models.
- Handling automated third-party dependency upgrades (e.g., Dependabot patches), which skip generation and route directly to the decoupled execution suite.

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| PR File Patch Context | GitHub Actions Workflow Environment | Extracted via `git diff` or changed-files tracking actions on `pull_request.opened`. |
| File Extension Metadata | Workflow Parsing Layer | Used to map source file types (e.g., `.py`, `.java`, `.ts`) to native language compilation modes. |
| Security System Prompt | Agent Internal Configuration | Embedded AppSec persona prompt directing the model to target fuzzing and language-specific exceptions. |
| OIDC Handshake Token | GitHub OIDC Provider | Temporary cryptographically signed web identity JWT exchanged for AWS runtime access. |

The agent is entirely **stateless** between runs, operating directly on the ephemeral code footprint pulled down into the runner's workspace container.

## 4. Permitted Tools / Authorization Boundary

The agent's assumed AWS IAM role and GitHub workspace configuration MUST be restricted to the following boundary. No long-lived cloud keys are stored; permission is strictly gated via OpenID Connect (OIDC).

| Layer / Service | Action | Resource / Scope |
| :--- | :--- | :--- |
| AWS Bedrock | `bedrock:InvokeModel` | `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet*` |
| GitHub Repository | `contents:read` | Checked out local workspace layer inside the execution runner container. |
| GitHub Repository | `contents:write` | Dynamic Git push privileges strictly scoped to target branch (`github.head_ref`). |
| GitHub Actions | `id-token:write` | Required to exchange a secure cryptographic OIDC token with the AWS STS boundary. |

## 5. Explicit Denies (Posture & Execution Invariants)

To ensure structural safety, prevent recursive execution bills, and avoid token abuse, the following invariants are enforced.

| Restriction | Type | Reason |
| :--- | :--- | :--- |
| No Execution on Bot Actors | Workflow Level (`if` gate) | The workflow must terminate if `github.actor == 'github-actions[bot]'`. This completely prevents infinite loops. |
| No Native Test Execution | Workflow Step Separation | The generation agent must never execute the tests. Doing so delays feedback loops and breaks workspace isolation boundaries. |
| No Direct Commits to `main` | Branch Protection Guard | The agent is explicitly denied branch targeting outside of `github.head_ref`. Direct writes to production lineage are strictly blocked. |
| Block Model Mutation APIs | AWS IAM Restriction | Access to `bedrock:CreateModelCustomizationJob` or storage configurations is forbidden. |

## 6. Behavior

A run proceeds in the following deterministic sequence:

```text
[Dev Opens PR] ──► [Filter: Not Bot?] ──► [Detect Source Language] ──► [OIDC Handshake] ──► [Invoke Bedrock] ──► [Git Push to Branch]

```

1. **Trigger Evaluation:** A pull request is initialized. The workflow validates that a human developer initiated the action, bypassing execution if a bot action is detected.

2. **Workspace Setup & Language Detection:** The runner fetches the codebase repository files. It scans the files changed in the pull request to identify file extensions, defining the programming language and target framework framework parameters.

3. **AWS OIDC Authentication:** The `aws-actions/configure-aws-credentials` block issues an ephemeral OIDC request token, authenticating the runner directly into AWS without secrets.

4. **Context Synthesis & Model Call:** Changed source modules are parsed. The system packages the raw code along with an optimization prompt detailing explicit test instructions tailored to that specific framework's ecosystem, dispatching the collection to Claude 3.5 Sonnet via `bedrock:InvokeModel`.

5. **Payload Parsing & File Generation:** The response is handled cleanly, extracting native test scripts and placing them in the language-appropriate test directory mirroring the source framework structure.

6. **Remote Repository Sync:** The runner updates local Git signatures to `github-actions[bot]`, batches the structural test files, runs `git commit`, and pushes the delta upstream to the developer's branch.

7. **Handoff to Decoupled Execution:** The generation workflow exits successfully. The upstream push triggers the secondary language-specific execution gate workflow to execute the test suite.

## 7. Outputs / Findings

The agent outputs concrete test code files written directly to the target feature repository branch. Every script produced must match the following architectural constraints:

- **Language Alignment:** All test files must be written in the exact same programming language as the application file modified by the developer.
- **Naming & Path Conventions:** All files must conform to the target language's native naming patterns (e.g., `tests/test_*.py` for Python, `src/test/java/*Test.java` for Java, `*.test.ts` for TypeScript).
- **AppSec Testing Coverage:** Generated test structures must include explicit parameters verifying edge-case conditions, boundary inputs, type mismatches, and exception testing blocks native to that language's runtime.

## 8. Failure Handling

- **AWS Bedrock Throttling (HTTP 429):** The python agent script handles exponential backoff delays with random jitter across 5 programmatic retry sweeps. If limits are hit, the execution job errors out, adding a failure summary alert page directly onto the PR.
- **Git Push Race Conflicts:** If a developer pushes updates to their branch while the AI is computing tests, the remote push is rejected. The workflow uses forced reconciliation flags or falls back to gracefully exiting, allowing the subsequent human commit to clean up and re-trigger.
- **Unsupported Language Match:** If a pull request modifies files belonging to a language not yet supported by the prompt parser mapping, the workflow exits gracefully with an informational step summary warning, bypassing Bedrock invocation.

## 9. Acceptance Criteria (Given/When/Then)

### AC-1 — Unit Test Language Matches Application Source Code

- **Given** a human developer opens a fresh pull request containing changes to a Java module (`.java`),
- **When** the workflow evaluates the entry criteria and detects the language parameter,
- **Then** the agent initializes execution, constructs testing scripts written in Java utilizing `JUnit` syntax, and safely pushes files into the feature branch.

### AC-2 — Workflow Terminal Bypass on Bot Inputs (GATING)

- **Given** a push or sync action initiated by `github-actions[bot]` (such as the agent's own automated file save event),
- **When** the workflow execution engine runs its global entry conditionals,
- **Then** the job halts execution immediately without calling Bedrock, eliminating the risk of infinite runner execution loops. **Gating in CI.**

### AC-3 — Authentication Operates Securely via OIDC (GATING)

- **Given** the execution run initiates AWS connection logic,
- **When** credentials validation runs via `configure-aws-credentials`,
- **Then** identity verification passes cleanly via asymmetric token exchange with zero hardcoded repository secrets or long-lived API keys. **Gating in CI.**

### AC-4 — Functional Handoff to Secondary Test Runner

- **Given** the test generation agent finishes uploading files back to the origin repository branch,
- **When** the branch configuration syncs,
- **Then** the generation workflow cleanly completes execution, instantly triggering the standalone decoupled multi-language test runner framework via standard webhook synchronization hooks.

## 10. Eval Mapping Table

| AC | Verification Mechanism | Validation Context | Gating |
| :--- | :--- | :--- | :--- |
| **AC-1** | Language Alignment Check | Validate that test payloads perfectly match the target source file extensions. | No |
| **AC-2** | Actor Conditional Check | Verify bot actors fail open and exit the pipeline immediately. | **Yes** |
| **AC-3** | OIDC Token Assertions | Verify cloud role assumption rejects standard static credentials. | **Yes** |
| **AC-4** | Inter-Workflow Handoff | Ensure successful generation pipeline completion initiates the execution gate. | No |