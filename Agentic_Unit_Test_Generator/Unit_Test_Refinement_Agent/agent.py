"""AgentCore entrypoint for the Unit Test Refinement Agent.

Thin wrapper around generator.refine_tests — all reasoning/retry logic lives
there so it can be tested without the AgentCore runtime (see local_test.py).
"""
try:
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
    app = BedrockAgentCoreApp()
except ImportError:
    app = None  # For local testing without the AgentCore runtime

from generator import refine_tests
from github_input import (
    derive_source_basename,
    fetch_multiple_from_github,
    find_source_file_by_basename,
)

TESTS_DIR = "Agentic_Unit_Test_Generator/tests"


def _invoke_impl(payload: dict) -> dict:
    source_file_path = payload.get("file_path")
    test_file_path = payload.get("test_file_path")
    repo = payload.get("repo")
    ref = payload.get("ref")
    source_code = payload.get("source_code")
    test_code = payload.get("test_code")

    if not test_file_path:
        return {"status": "failed", "error": "test_file_path is required"}
    if not source_code and not (repo and ref):
        return {"status": "failed", "error": "either source_code, or both repo and ref, are required"}
    if not test_code and not (repo and ref):
        return {"status": "failed", "error": "either test_code, or both repo and ref, are required"}
    if not source_file_path and not (repo and ref):
        return {"status": "failed", "error": "file_path is required unless repo and ref are given (to resolve it)"}

    language_override = payload.get("language")
    framework_override = payload.get("framework")
    failure_logs = payload.get("failure_logs", "")

    try:
        if not source_file_path:
            basename = derive_source_basename(test_file_path)
            source_file_path = find_source_file_by_basename(repo, ref, basename, TESTS_DIR)

        if not source_code or not test_code:
            fetched = fetch_multiple_from_github(repo, [source_file_path, test_file_path], ref)
            source_code = source_code or fetched.get(source_file_path)
            test_code = test_code or fetched.get(test_file_path)

        return refine_tests(source_code, test_code, source_file_path, test_file_path, language_override, framework_override, failure_logs)
    except ValueError as e:
        return {"status": "failed", "error": str(e)}


if app is not None:
    @app.entrypoint
    def invoke(payload: dict) -> dict:
        return _invoke_impl(payload)
else:
    def invoke(payload: dict) -> dict:
        return _invoke_impl(payload)


if __name__ == "__main__":
    if app is not None:
        app.run()
    else:
        raise RuntimeError("bedrock-agentcore not installed. Use local_test.py for local testing.")
