| Key | Value |
| :--- | :--- |
| **spec_id** | SPEC-ABC-0002 |
| **capability** | unit-test-refinement-agent |
| **status** | Draft |
| **owner** | Aryan Panikar |
| **reviewers** | Peer |
| **approver** | Rehman |
| **prd** | - |
| **jira_epic** | - |
| **version** | 0.0.1 |
| **created** | 2026-06-24 |
| **last_updated** | 2026-06-24 |

# spec.md — Test Refinement Agent

> This is the **executable contract**. The GitHub Actions review hook, pull request 
> comment parsing engine, and path-based refinement iteration logic trace back 
> directly to this file. Posture safety checks (AC-2, AC-3) are **gating in CI**: 
> any pipeline breakdown or unauthorized repository mutation fails the build.

## 1. Summary

The Unit Test Refinement Agent is an event-driven automation layer that optimizes and corrects generated unit tests based on human reviewer feedback, utilizing path-filtering guardrails to distinguish between application code changes and test suite corrections. When a reviewer submits a "Request Changes" review on a pull request, a dedicated GitHub Actions workflow intercepts the submission event. 

The agent runs a target-filtering pre-flight check on the modified file paths. If the reviewer's feedback targets generated test scripts, the agent ingests the specific comments, lines of code referenced, and the existing failing test assets. It passes this coupled context securely to AWS Bedrock (Claude 3.5 Sonnet) to perform localized, iterative modifications to the test suite. The updated test files are then pushed natively back into the developer's source branch, passing control back to the independent Test Execution Workflow. If the comments exclusively target the developer's feature code, the agent terminates without action.

## 2. Goals / Non-Goals

### Goals
- Automatically trigger on PR review events specifically when the state is set to `changes_requested`.
- **Implement File-Path Target Filtering** to programmatically determine if incoming critiques belong to human application code or AI-generated tests.
- Extract and parse pull request review comments, associated diff hunks, and target test files.
- Invoke AWS Bedrock using short-lived OpenID Connect (OIDC) identity tokens to refine existing test code dynamically based on human feedback.
- Preserve unchanged testing modules while rewriting sections identified as inaccurate, missing, or overly permissive by the reviewer.
- Push refined test suites back to the feature branch to automatically initiate re-execution under the standalone Test Execution Workflow.

### Non-goals
- Modifying, refactoring, or editing the developer's underlying application feature code under any circumstance.
- Processing comments or reviews that exclusively target core business logic or application modules.
- Executing or compiling the modified test files natively within the refinement workflow container runner.
- Generating test baselines from scratch (delegated entirely to `SPEC-ABC-0001`).

## 3. Inputs

| Input | Source | Notes |
| :--- | :--- | :--- |
| Review State | `pull_request_review` event payload | Verified against `submitted` types; execution gates strictly on `changes_requested` values. |
| Commented File Paths | GitHub Action Event Payload | Extracted from `github.event.review.links.comments` or `comments[*].path` to evaluate routing. |
| Reviewer Comments | GitHub Action Event Payload | Ingests `github.event.review.body` along with granular inline comments (`comments[*].body`). |
| Target Code Base | GitHub Workspace Runner | Checks out the active feature branch containing the previously generated test files. |
| OIDC Web Identity | GitHub OIDC Provider | Ephemeral JSON Web Token exchanged with AWS STS to authenticate model requests safely. |

The agent is **stateless** across distinct pull request review cycles, treating the combined state of the active branch files and current comment thread as the source of truth.

## 4. Permitted Tools / Authorization Boundary

The agent's assumed AWS IAM role and repository access criteria are tightly sandboxed to enforce the principle of least privilege.

| Layer / Service | Action | Resource / Scope |
| :--- | :--- | :--- |
| AWS Bedrock | `bedrock:InvokeModel` | `arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet*` |
| GitHub Repository | `pull_requests:read` | Grants permissions to query PR timelines, conversation strings, and file history metadata. |
| GitHub Repository | `contents:write` | Dynamic Git write privileges restricted strictly to the current feature branch (`github.head_ref`). |
| GitHub Actions | `id-token:write` | Mandatory rule to request the cryptographic identity handshake token for AWS authentication. |

## 5. Explicit Denies (Posture & Execution Invariants)

| Restriction | Type | Reason |
| :--- | :--- | :--- |
| Block Non-Test Feedback | File Path Guard | The agent is explicitly denied execution if 100% of the review comments target application feature code files. |
| Block Approval Actions | Event Guard (`if` evaluation) | The agent must exit instantly if the review state is `approved` or `commented`. It executes *only* on rejection patterns. |
| No Execution on Bot Actions | Workflow Loop Guard | The runtime instantly drops execution if `github.event.review.user.type == 'Bot'`. This halts loops between automated testing systems. |
| No Source Code Mutation | Directory Scope Isolation | The workspace context blocks the tool layer from committing changes to non-test file structures. |
| Block Cloud Configuration APIs | AWS IAM Restriction | Policy settings forbid structural model fine-tuning or model lifecycle interactions. |

## 6. Behavior

A refinement loop executes according to the following deterministic sequence (mapping directly to Phase V of the pipeline architecture):

```text
[PR Changes Requested] ──► [Path Filtering Gate] ──► [Gather Test Comments] ──► [Invoke Bedrock Agent] ──► [Refine Tests] ──► [Push to Branch]

```

1. **Trigger Evaluation:** A reviewer submits a review. The workflow validates that the state equals `changes_requested` and confirms a human actor initiated it, bypassing execution if conditions fail.
2. **Path Filtering Gate:** The runner inspects the `comments[*].path` array from the GitHub webhook payload.
* If no comments match target test path patterns (e.g., `/test_*.py`, `/src/test/`, `/*.test.ts`), the workflow logs *"Review targets application feature code. Bypassing AI agent."* and terminates gracefully with an exit code `0`.
* If test file comments are discovered, the workflow proceeds to step 3.


3. **Comment Ingestion:** The workflow engine extracts the markdown string body of the review along with all single-line inline code review notes attached *specifically* to test file paths, completely filtering out general application code chatter.
4. **AWS OIDC Authentication:** The container runner initiates a cryptographic handshake with AWS Security Token Service (STS) using OpenID Connect, securely logging in without passwords.
5. **Model Context Synthesis:** The script parses the target test files and packages the existing test code, the original application code delta, and the compiled test-relevant critique notes into an operational payload context. It maps the reviewer's markdown remarks and line numbers directly to the test code blocks to build a targeted Feedback-to-Code Matrix.
6. **Targeted Test Refinement:** The package is dispatched to Claude 3.5 Sonnet via `bedrock:InvokeModel` using a strict Minimal Mutation prompt constraint. The model is forbidden from rewriting unaffected code blocks. It interprets instructions exclusively to address logic gaps, remove over-permissive assertions, or correct test structure bugs to satisfy the human reviewer's intent.
7. **Workspace Sync & Push:** The corrected test suites are extracted from the AI payload, stripping any conversational text. The raw test code is validated locally using native language compilers (e.g., `python -m py_compile` or syntax parsers) to guarantee syntax integrity. If valid, changes are committed under the signature `github-actions[bot]` and pushed upstream to the feature branch. If syntax errors are caught, the payload is rejected before the commit step to prevent workspace pollution.
8. **Handoff to Independent Runner:** The workflow terminates successfully. The upstream push triggers the standalone `TEST EXECUTION WORKFLOW` via a `synchronize` hook event to re-evaluate the suite against the regression gate.

## 7. Outputs / Findings

The agent delivers optimized, structurally stable unit test files written back directly into the active PR feature workspace branch.

* **Language Cohesion:** Refined test suites must maintain strict linguistic continuity with the source language format specified by the tracking directory hierarchy.
* **Traceability Markers:** Modified blocks must append internal descriptive comment blocks mapping the refactoring directly to the reviewer's issue context for clean manual audit trails (e.g., `// Refined by AI based on Reviewer Comment: <Summary>`).
* **Framework Uniformity:** Outputs must maintain exact semantic alignment with the framework footprint initialized in the baseline generation pass (e.g., matching standard assertion layouts).
* **Payload Isolation Guardrail:** If the AI response payload contains modifications to application business logic files instead of test directory paths, the validation layer throws a `PostureViolationError`, scrubs the workspace, and aborts the sync process.

## 8. Failure Handling

* **Pure Feature Code Feedback:** Handled natively by the Path Filtering Gate; completely prevents the agent from triggering or burning tokens when human code is the target of a change request.
* **Ambiguous Feedback Context:** If the reviewer leaves an empty change request or general comments without specifying contextual files or actionable requests, the script registers an information message onto the PR workspace summary and exits cleanly without invoking Bedrock.
* **Merge Conflicts during Local Sync:** If concurrent human commits interrupt the runner's tracking lineage, the file update push fails. The engine aborts, requiring the developer to execute a standard branch sync to normalize tracking histories.
* **Bedrock Performance Throttling:** Network exceptions or API limits are managed via exponential backoff routines with random jitter constraints up to 5 successive tracking sweeps before raising a failure status.

## 9. Acceptance Criteria (Given/When/Then)

### AC-1 — Test Architecture Refines Automatically on Reviewer Request

* **Given** an open pull request where a senior engineer submits a review stating `Request Changes` alongside explicit corrections for a test file path (e.g., `tests/test_auth.py`),
* **When** the workflow evaluates the webhook event parameters and path configurations,
* **Then** the agent initializes execution, aggregates inline text notes, updates the targeted lines of code via Bedrock, and commits the updates back to the developer's branch.

### AC-2 — Agent Aborts Gracefully on Pure Feature Code Requests (GATING)

* **Given** an open pull request where a reviewer requests changes but *exclusively* targets core application code paths (e.g., `src/main/auth.py`),
* **When** the path-filtering engine scans the `comments[*].path` array,
* **Then** the workflow logs a bypass statement and exits successfully with an exit code `0` without invoking Bedrock. **Gating in CI.**

### AC-3 — Guardrail Clearance on Approval Events (GATING)

* **Given** a human reviewer flags a pull request workspace branch as `Approved`,
* **When** the tracking workflow parses the incoming event block,
* **Then** the job completely terminates execution without querying Bedrock, preserving the approved code and avoiding recursive runtime execution loops. **Gating in CI.**

### AC-4 — Complete Access Restriction via OIDC Identity Gates (GATING)

* **Given** the agent triggers file updates on an unverified or unauthorized external repository,
* **When** cloud credentials setup runs via the identity connection provider,
* **Then** the role assumption handshake is rejected at the AWS perimeter, blocking unauthorized model use. **Gating in CI.**

### AC-5 — Functional Re-Validation Sequencing

* **Given** the test refinement agent updates the files on the development target workspace,
* **When** the remote branch completes its update synchronization,
* **Then** the refinement container exits cleanly, handing off to the decoupled `test-runner.yml` framework to evaluate the corrected code structure.

## 10. Eval Mapping Table

| AC | Verification Mechanism | Validation Context | Gating |
| --- | --- | --- | --- |
| `AC-1` | Feedback Iteration Check | Confirm reviewer markdown remarks convert into precise test code updates. | No |
| `AC-2` | Path Filtering Interceptor | Verify the pipeline exits without token spend when only core application logic is critiqued. | No |
| `AC-3` | State Conditional Filter | Ensure approval and generic comment payloads bypass the AI execution loop entirely. | No |
| `AC-4` | Cryptographic Token Check | Assert that cloud connection loops fail without verified OIDC handshakes. | No |
| `AC-5` | Execution Handoff Sync | Verify that branch updates trigger the standalone Test Execution Workflow. | No |
