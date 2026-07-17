# Project: Unit Test Refinement Agent

## Context
This directory (`Agentic_Unit_Test_Generator/Unit_Test_Refinement_Agent`) contains a clone of the `Unit_Test_Generator_Agent`. 
Your task is to adapt these files into a **Refinement Agent**. Instead of generating tests from scratch, this agent will take an existing source file, an existing unit test file, and potentially a failure log/report, and output a corrected, refined test file. This will be integrated into `.github/workflows/refine-unit-test.yml` via a wrapper script (`Agentic_Unit_Test_Generator/scripts/refine_unit_test.py`).

## Strict Architectural Constraints
- **Deployment**: AWS Bedrock AgentCore runtime (`direct_code_deploy`) in `ap-southeast-2`[cite: 1].
- **Model Parameters**: Must use `global.anthropic.claude-sonnet-5`[cite: 1]. Ensure `temperature` is strictly omitted from the `inferenceConfig` to avoid validation errors[cite: 1].
- **Response Parsing**: Retain the `_extract_text` logic in `generator.py` to safely concatenate text blocks and ignore reasoning blocks (preventing `KeyError: 'text'`)[cite: 1].
- **Network Boundary**: No S3 access permitted[cite: 1]. Code must be fetched via the GitHub Contents API using a Personal Access Token (PAT) retrieved from AWS Secrets Manager (`secretsmanager:GetSecretValue`)[cite: 1].
- **Payload Contract**: The agent accepts `repo`, `ref` (commit SHA), and file paths[cite: 1]. It returns syntactically valid code in the response payload, and the CI wrapper script is responsible for writing the file to disk[cite: 1].

## Required File Modifications
1. **`github_input.py` & `agent.py`**: Extend the logic to fetch *both* the source code file and the existing test file from GitHub. Update the invocation payload to accept `test_file_path` and `failure_logs` (if applicable).
2. **`prompts.py`**: Rewrite the system and user prompts. The agent must act as a test refiner/fixer. It should take the source code, the existing tests, and the failure context to output a corrected test file. Retain the strict anti-vacuous instructions (no `assert True`) and security test categories[cite: 1].
3. **`generator.py`**: Update the generation loop to pass the new context (existing test code, error logs) to the model. Retain the deterministic retry loop (max 3 attempts)[cite: 1].
4. **`validators.py`**: Keep the AST-based validation to reject empty bodies, `assert True`, or missing assertions on the refined output[cite: 1].

## Next Steps for Claude
1. Review the copied files in this directory.
2. Update `agent.py`, `generator.py`, `prompts.py`, and `github_input.py` to match the refinement use case outlined above.
3. Help adapt `Agentic_Unit_Test_Generator/scripts/refine_unit_test.py` to invoke this new agent.
4. Validate locally using `local_test.py --via-github`.