#!/usr/bin/env python3
"""
Test Agent 1 (CIAM Intent Classifier) with CORRECT input format
Agent 1 expects Jira ticket data, NOT pre-classified intents
"""

import json
import subprocess
import base64
import sys
from datetime import datetime

class Agent1CorrectTester:
    def __init__(self, agent_runtime_arn: str):
        self.agent_arn = agent_runtime_arn
        self.results = []

    def invoke_agent(self, issue_key: str, summary: str, description: str, run_id: str) -> dict:
        """Invoke Agent 1 with correct Jira ticket format"""
        payload = {
            "issue_key": issue_key,
            "summary": summary,
            "description": description
        }

        try:
            payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()

            cmd = [
                "aws", "bedrock-agentcore", "invoke-agent-runtime",
                "--agent-runtime-arn", self.agent_arn,
                "--payload", payload_b64,
                "--region", "us-east-1",
                "--no-verify-ssl",
                "/tmp/agent1_response.json"
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                return {"status": 500, "error": result.stderr, "success": False}

            response = json.loads(result.stdout)

            # Read response body
            try:
                with open("/tmp/agent1_response.json") as f:
                    body = f.read()
            except:
                body = ""

            return {
                "status": response.get('statusCode'),
                "session_id": response.get('runtimeSessionId'),
                "body": body,
                "success": response.get('statusCode') == 200
            }

        except Exception as e:
            return {"status": 500, "error": str(e), "success": False}

    def run_test_case(self, test_case: dict) -> dict:
        """Run a single test case"""
        test_id = test_case['id']
        issue_key = test_case['issue_key']
        summary = test_case['summary']
        description = test_case['description']
        expected_intent = test_case['expected_intent']

        print(f"\n{'='*80}")
        print(f"🧪 Test: {test_id} - {test_case['title']}")
        print(f"{'='*80}")
        print(f"Jira Key:  {issue_key}")
        print(f"Summary:   {summary}")
        print(f"Description: {description[:100]}...")
        print(f"Expected Intent: {expected_intent}")
        print()

        # Invoke agent
        print("📡 Invoking Agent 1...")
        response = self.invoke_agent(issue_key, summary, description, test_id)

        print(f"Status: {response['status']}")

        if response['success']:
            # Parse and extract intent
            try:
                body = json.loads(response['body'])
                actual_intent = body.get('intent', 'ERROR')
                confidence = body.get('confidence', 0.0)
                extracted_email = body.get('extracted_email', 'N/A')

                print(f"✅ Agent responded successfully")
                print(f"   Classified Intent: {actual_intent}")
                print(f"   Confidence: {confidence:.2f}")
                print(f"   Extracted Email: {extracted_email}")

                # Check if classification matches expected
                match = "✅ CORRECT" if actual_intent == expected_intent else "❌ INCORRECT"
                print(f"   {match}")

                result = {
                    "test_id": test_id,
                    "title": test_case['title'],
                    "status": response['status'],
                    "success": response['success'],
                    "expected_intent": expected_intent,
                    "actual_intent": actual_intent,
                    "confidence": confidence,
                    "extracted_email": extracted_email,
                    "correct": actual_intent == expected_intent
                }
            except:
                print(f"❌ Error parsing response")
                result = {
                    "test_id": test_id,
                    "title": test_case['title'],
                    "status": response['status'],
                    "success": False,
                    "correct": False
                }
        else:
            print(f"❌ FAIL - {response.get('error', 'Unknown error')}")
            result = {
                "test_id": test_id,
                "title": test_case['title'],
                "status": response['status'],
                "success": False,
                "correct": False
            }

        self.results.append(result)
        return result

    def run_all_tests(self, test_cases: list):
        """Run all test cases"""
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*15 + "AGENT 1 - CORRECT INPUT FORMAT TEST SUITE" + " "*21 + "║")
        print("║" + " "*20 + "Testing with Jira Ticket Data" + " "*29 + "║")
        print("╚" + "="*78 + "╝")
        print(f"\nTotal Tests: {len(test_cases)}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        for test_case in test_cases:
            self.run_test_case(test_case)

        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.results if r['success'])
        correct = sum(1 for r in self.results if r.get('correct', False))
        total = len(self.results)

        print("\n\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*25 + "TEST SUMMARY" + " "*41 + "║")
        print("╠" + "="*78 + "╣")
        print(f"║ Total Tests:        {total:<55}║")
        print(f"║ Responded:          {passed:<55}║")
        print(f"║ Correct Intent:     {correct:<55}║")
        pass_rate = (passed / total * 100) if total > 0 else 0
        correct_rate = (correct / total * 100) if total > 0 else 0
        print(f"║ Response Rate:      {pass_rate:.1f}% {' '*49}║")
        print(f"║ Classification Accuracy: {correct_rate:.1f}% {' '*44}║")
        print("╠" + "="*78 + "╣")
        print("║ Robustness Assessment:                                              ║")

        if correct_rate == 100:
            print("║ ✅ EXCELLENT - Perfect classification, Agent 1 is production-ready ║")
        elif correct_rate >= 80:
            print("║ ⚠️  GOOD - Most classifications correct, minor issues              ║")
        elif correct_rate >= 60:
            print("║ ⚠️  FAIR - Several misclassifications, needs work                  ║")
        else:
            print("║ ❌ POOR - Many misclassifications, needs significant improvements  ║")

        print("╚" + "="*78 + "╝")

        print("\n📋 Detailed Results:")
        print("-" * 80)
        for result in self.results:
            status_icon = "✅" if result.get('correct') else "❌"
            expected = result.get('expected_intent', '?')
            actual = result.get('actual_intent', '?')
            print(f"{status_icon} {result['test_id']}: {result['title']:<40}")
            print(f"   Expected: {expected} | Actual: {actual}")
        print("-" * 80)


def main():
    # Load test cases
    with open("agent1_correct_test_cases.json") as f:
        test_data = json.load(f)

    test_cases = test_data['test_scenarios']

    agent1_arn = "arn:aws:bedrock-agentcore:us-east-1:786063285476:runtime/ciamintentclassifier-a0h3meCoOo"

    print(f"\n✅ Using Agent 1: {agent1_arn}\n")

    tester = Agent1CorrectTester(agent1_arn)
    tester.run_all_tests(test_cases)

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
