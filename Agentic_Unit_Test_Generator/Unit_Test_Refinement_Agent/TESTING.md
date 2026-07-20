# Testing Guide: Unit Test Refinement Agent

## Structure Validation (No AWS Required)

Verify all files are syntactically correct:
```bash
python3 validate_structure.py
```

Expected output:
```
✓ agent.py: valid
✓ generator.py: valid
✓ prompts.py: valid
✓ github_input.py: valid
✓ validators.py: valid
✓ language_framework.py: valid
✓ local_test.py: valid

✓ All files structurally valid
```

## Local Testing (Requires AWS Credentials)

### Prerequisites
1. Python 3.11+ 
2. AWS credentials configured (`aws configure` or OIDC/IAM role)
3. Dependencies installed:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install boto3 requests
   ```

### Test Cases

#### Test Case 1: Inline Source + Test Code (No GitHub)
Fastest iteration — all code passed inline.

```bash
source .venv/bin/activate
python local_test.py \
  /path/to/source_file.py \
  /path/to/test_file.py
```

Example:
```bash
python local_test.py \
  Agentic_Unit_Test_Generator/scripts/calculator.py \
  Agentic_Unit_Test_Generator/tests/test_calculator.py
```

#### Test Case 2: With Failure Logs
Test with reviewer feedback or failure context.

```bash
python local_test.py \
  /path/to/source_file.py \
  /path/to/test_file.py \
  --failure-logs /path/to/feedback.txt
```

Example feedback file (`feedback.txt`):
```
Line 42: Test should verify division by zero raises ValueError, not catches it
Line 15: assert_equal() is deprecated, use assert_equal_exact()
Line 28: Missing edge case for negative infinity
```

Run:
```bash
python local_test.py \
  Agentic_Unit_Test_Generator/scripts/calculator.py \
  Agentic_Unit_Test_Generator/tests/test_calculator.py \
  --failure-logs /tmp/feedback.txt
```

#### Test Case 3: GitHub Fetch (Exercises Full Contract)
Fetches both source and test files from GitHub at a pinned commit.

```bash
python local_test.py \
  Agentic_Unit_Test_Generator/scripts/calculator.py \
  Agentic_Unit_Test_Generator/tests/test_calculator.py \
  --via-github \
  --ref <commit_sha> \
  --repo netSkope/GIS-SecEng-Intern
```

Requires:
- AWS credentials with `secretsmanager:GetSecretValue` on `GITHUB_PAT_SECRET_ARN`
- `GITHUB_PAT_SECRET_ARN` environment variable set

```bash
export GITHUB_PAT_SECRET_ARN=arn:aws:secretsmanager:ap-southeast-2:ACCOUNT:secret:github-pat-xyz
python local_test.py \
  Agentic_Unit_Test_Generator/scripts/calculator.py \
  Agentic_Unit_Test_Generator/tests/test_calculator.py \
  --via-github \
  --ref $(git rev-parse HEAD) \
  --repo netSkope/GIS-SecEng-Intern
```

### Expected Output

Success (status: ok):
```json
{
  "status": "ok",
  "language": "python",
  "framework": "pytest",
  "attempts": 1,
  "rejection_history": []
}

--- REFINED TEST CODE ---

import pytest
from calculator import divide

def test_divide_normal():
    """Dividing two positive numbers returns correct result."""
    assert divide(10, 2) == 5
    assert divide(3, 2) == 1.5

def test_divide_by_zero_raises():
    """Dividing by zero raises ValueError."""
    with pytest.raises(ValueError):
        divide(10, 0)
```

Failure (status: failed):
```json
{
  "status": "failed",
  "test_code": null,
  "language": "python",
  "framework": "pytest",
  "attempts": 3,
  "rejection_history": [
    {
      "attempt": 1,
      "issues": ["vacuous_test:test_division"]
    },
    {
      "attempt": 2,
      "issues": ["vacuous_test:test_edge_case"]
    }
  ]
}

FAILED — no refined test code produced.
```

## Integration Testing (Full Workflow)

Once deployed to Bedrock AgentCore, test the full CI flow:

### Step 1: Create a Test PR
```bash
git checkout -b test/refinement
# Make a small change to a test file with intentional issue
# e.g., change `assert True` to correct assertion
git add Agentic_Unit_Test_Generator/tests/test_something.py
git commit -m "Test refinement"
git push origin test/refinement
```

### Step 2: Leave Reviewer Feedback
On the PR, request changes on specific lines of the test file:
```
Line 15: This test doesn't validate the error case
Line 28: Please add a test for empty input
```

### Step 3: Monitor Workflow
The `refine-unit-test.yml` workflow will:
1. Detect the review state
2. Collect inline comments
3. Invoke the Refinement Agent
4. Commit refined tests back to the branch
5. Post results to PR comment

Check workflow logs:
```bash
gh run view --log $(gh run list -L1 -q)
```

### Step 4: Verify Refined Tests
```bash
git log --oneline | head -5
# Should show commit like "Refine Generated Unit Test For test_something.py Per Review Feedback"

git show HEAD
# Should display the refined test code with corrections
```

## Debugging

### Issue: `ModuleNotFoundError: No module named 'boto3'`
```bash
# Install dependencies in venv
python3 -m venv .venv
source .venv/bin/activate
pip install boto3 requests
```

### Issue: AWS credential errors
```bash
# Verify credentials
aws sts get-caller-identity

# Check Secrets Manager access
aws secretsmanager get-secret-value \
  --secret-id $GITHUB_PAT_SECRET_ARN \
  --region ap-southeast-2
```

### Issue: Bedrock invocation errors
```bash
# Verify model access
aws bedrock list-foundation-models \
  --region ap-southeast-2 | grep claude-sonnet-5

# Check bedrock:Converse permission
aws iam get-role-policy --role-name <execution-role> --policy-name <policy-name>
```

## Performance Notes

- **Inline mode** (no GitHub fetch): ~3-5 seconds per refinement
- **GitHub mode** (with fetch): ~5-8 seconds (1-2s network + 3-5s model)
- **With retries** (failed validations): multiply by attempt count (max 3)
- **Feedback processing**: negligible (<100ms)

## Cleanup

Remove local test artifacts:
```bash
rm -rf .venv validate_structure.py
```
