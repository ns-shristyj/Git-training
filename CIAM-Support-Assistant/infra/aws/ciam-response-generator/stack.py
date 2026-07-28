"""
CDK Stack for CIAM Response Generator (Agent 5)

Deploys Agent 5 to Bedrock AgentCore with proper IAM permissions,
logging, and integration with the CIAM orchestrator.
"""

import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_bedrock as bedrock,
    Duration,
    RemovalPolicy,
)
from constructs import Construct


class CIAMResponseGeneratorStack(Stack):
    """
    Bedrock AgentCore stack for CIAM Response Generator (Agent 5).

    Security model:
    - No reads from DynamoDB, Auth0, Salesforce, or Bedrock KB
    - No writes except audit logging (S3, CloudWatch)
    - Output-only to Slack/Jira via Secrets Manager credentials
    """

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ====================================================================
        # LAMBDA EXECUTION ROLE
        # ====================================================================

        agent5_role = iam.Role(
            self,
            "Agent5ExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name="ciam-response-generator-execution-role",
            description="Execution role for CIAM Response Generator Agent (Agent 5)",
        )

        # CloudWatch Logs (basic Lambda execution)
        agent5_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSLambdaBasicExecutionRole"
            )
        )

        # Bedrock AgentCore invocation (to be called by orchestrator)
        agent5_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeAgent",
                ],
                resources=["*"],  # AgentCore manages the ARN
            )
        )

        # Secrets Manager access (for Slack/Jira tokens — Phase 1C)
        agent5_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[
                    f"arn:aws:secretsmanager:*:*:secret:ciam-agent/slack-*",
                    f"arn:aws:secretsmanager:*:*:secret:ciam-agent/jira-*",
                ],
            )
        )

        # KMS decrypt (for Secrets Manager)
        agent5_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:Decrypt"],
                resources=["*"],  # CIAM CMK — should be parameterized
                conditions={
                    "StringEquals": {
                        "kms:ViaService": [
                            f"secretsmanager.{self.region}.amazonaws.com"
                        ]
                    }
                },
            )
        )

        # EXPLICIT DENIES (posture invariants)
        agent5_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=[
                    "dynamodb:*",  # Agent 2 reads from DynamoDB
                    "bedrock:Retrieve",  # Agent 4 reads from KB
                    "bedrock:RetrieveAndGenerate",
                ],
                resources=["*"],
            )
        )

        agent5_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.DENY,
                actions=[
                    "secretsmanager:GetSecretValue",
                ],
                resources=[
                    # Only allow Slack/Jira tokens; deny all others
                    "arn:aws:secretsmanager:*:*:secret:ciam-agent/auth0-*",
                    "arn:aws:secretsmanager:*:*:secret:ciam-agent/bedrock-*",
                ],
            )
        )

        # ====================================================================
        # CLOUDWATCH LOG GROUP
        # ====================================================================

        log_group = logs.LogGroup(
            self,
            "Agent5Logs",
            log_group_name="/ciam/response-generator/agent-logs",
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ====================================================================
        # LAMBDA FUNCTION
        # ====================================================================

        agent5_function = lambda_.Function(
            self,
            "Agent5Function",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="agent.app",  # Bedrock AgentCore handler
            code=lambda_.Code.from_asset(
                "../../../agents/05-response-generator"
            ),
            role=agent5_role,
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "AGENT_NAME": "ciam-response-generator",
                "AGENT_VERSION": "0.2.0",
                "LOG_GROUP": log_group.log_group_name,
            },
            description="CIAM Response Generator — Synthesis & Diagnosis Agent (Agent 5)",
        )

        # Grant CloudWatch Logs write access
        log_group.grant_write(agent5_function);

        # ====================================================================
        # BEDROCK AGENTCORE INTEGRATION
        # ====================================================================

        # Note: Actual Bedrock Agent creation is done via AWS Console or
        # separate CDK construct (bedrock-agent-construct) once the
        # Agent resource API is available.
        #
        # For now, the Lambda function is ready to be invoked by:
        # - The orchestrator (via AgentCore)
        # - Tests (directly)
        # - Manual invocation (for debugging)

        # ====================================================================
        # OUTPUTS
        # ====================================================================

        cdk.CfnOutput(
            self,
            "Agent5FunctionArn",
            value=agent5_function.function_arn,
            description="ARN of Agent 5 Lambda function",
        )

        cdk.CfnOutput(
            self,
            "Agent5FunctionName",
            value=agent5_function.function_name,
            description="Name of Agent 5 Lambda function",
        )

        cdk.CfnOutput(
            self,
            "Agent5LogGroup",
            value=log_group.log_group_name,
            description="CloudWatch Logs group for Agent 5",
        )

        cdk.CfnOutput(
            self,
            "Agent5ExecutionRoleArn",
            value=agent5_role.role_arn,
            description="ARN of Agent 5 execution role",
        )
