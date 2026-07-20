"""Core generation logic for the Unit Test Generator Agent.

Kept separate from the AgentCore entrypoint (agent.py) so it can be exercised
directly in a local Python process without spinning up the AgentCore runtime.
"""
import re

import boto3
from botocore.config import Config

from language_framework import detect_language_framework
from prompts import build_retry_message, build_system_prompt, build_user_message
from validators import check_generic_test_quality, check_python_test_quality

MODEL_ID = "global.anthropic.claude-sonnet-5"
REGION = "ap-southeast-2"
MAX_ATTEMPTS = 3
MAX_OUTPUT_TOKENS = 8192
BEDROCK_CLIENT_CONFIG = Config(read_timeout=300, connect_timeout=10, retries={"max_attempts": 0})

_CODE_BLOCK_PATTERN = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


def _extract_text(content_blocks: list[dict]) -> str:
    """Concatenates every text block in the response. Newer Claude models can
    emit non-text blocks first (e.g. reasoningContent) — content[0] is not
    reliably the text block."""
    return "".join(block["text"] for block in content_blocks if "text" in block)


def extract_code_block(text: str) -> str:
    match = _CODE_BLOCK_PATTERN.search(text)
    if not match:
        raise ValueError("no_code_block_found")
    return match.group(1).strip() + "\n"


def _module_path(file_path: str) -> str:
    return file_path.replace("/", ".").removesuffix(".py")


def _check_quality(test_code: str, language: str) -> list[str]:
    if language == "python":
        return check_python_test_quality(test_code)
    return check_generic_test_quality(test_code, language)


def generate_tests(
    source_code: str,
    file_path: str,
    language_override: str = None,
    framework_override: str = None,
) -> dict:
    language, framework = detect_language_framework(file_path, language_override, framework_override)
    module_path = _module_path(file_path)

    client = boto3.client("bedrock-runtime", region_name=REGION, config=BEDROCK_CLIENT_CONFIG)
    system_prompt = build_system_prompt(language, framework)

    messages = [
        {
            "role": "user",
            "content": [{"text": build_user_message(source_code, file_path, module_path, language, framework)}],
        }
    ]

    rejection_history = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = client.converse(
            modelId=MODEL_ID,
            system=[{"text": system_prompt}],
            messages=messages,
            inferenceConfig={"maxTokens": MAX_OUTPUT_TOKENS},
        )
        stop_reason = response.get("stopReason")
        model_text = _extract_text(response["output"]["message"]["content"])
        messages.append({"role": "assistant", "content": [{"text": model_text}]})

        try:
            test_code = extract_code_block(model_text)
        except ValueError:
            issue = "output_truncated_max_tokens" if stop_reason == "max_tokens" else "no_code_block_found"
            rejection_history.append({"attempt": attempt, "issues": [issue]})
            messages.append({"role": "user", "content": [{"text": build_retry_message([issue])}]})
            continue

        issues = _check_quality(test_code, language)
        if not issues:
            return {
                "status": "ok",
                "test_code": test_code,
                "language": language,
                "framework": framework,
                "attempts": attempt,
                "rejection_history": rejection_history,
            }

        rejection_history.append({"attempt": attempt, "issues": issues})
        messages.append({"role": "user", "content": [{"text": build_retry_message(issues)}]})

    return {
        "status": "failed",
        "test_code": None,
        "language": language,
        "framework": framework,
        "attempts": MAX_ATTEMPTS,
        "rejection_history": rejection_history,
    }
