"""AgentCore entrypoint for the Unit Test Generator Agent.

Thin wrapper around generator.generate_tests — all reasoning/retry logic lives
there so it can be tested without the AgentCore runtime (see local_test.py).
"""
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from generator import generate_tests
from github_input import fetch_source_from_github

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    file_path = payload.get("file_path")
    repo = payload.get("repo")
    ref = payload.get("ref")
    source_code = payload.get("source_code")

    if not file_path:
        return {"status": "failed", "error": "file_path is required"}
    if not source_code and not (repo and ref):
        return {"status": "failed", "error": "either source_code, or both repo and ref, are required"}

    language_override = payload.get("language")
    framework_override = payload.get("framework")

    try:
        if not source_code:
            source_code = fetch_source_from_github(repo, file_path, ref)
        return generate_tests(source_code, file_path, language_override, framework_override)
    except ValueError as e:
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    app.run()
