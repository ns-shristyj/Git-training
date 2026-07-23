"""
CIAM Database Agent — Agent 2
Spec:    SPEC-CIAM-0002
Version: 0.1.0

What this file does
-------------------
This is the entrypoint file that Amazon Bedrock AgentCore runs when the
orchestrator invokes Agent 2. It:

  1. Receives a user email from the routing envelope (Agent 1 output)
  2. Queries the NetskopeID DynamoDB table (read-only) via EmailIndex GSI
  3. Fetches recent account change history (last 30 days), if available
  4. Returns a structured AccountPayload to the orchestrator

Security model
--------------
The agent may call ONLY:
  - dynamodb:Query and dynamodb:GetItem on the NetskopeID table
  - No writes, no Auth0, no Salesforce, no other AWS services
The IAM execution role enforces this with explicit denies.
"""

import json
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, List, Any

import boto3
from botocore.exceptions import ClientError
from bedrock_agentcore import BedrockAgentCoreApp
from pydantic import BaseModel

# Configuration
AWS_REGION = "us-east-1"
DYNAMODB_TABLE = "NetskopeID"
DYNAMODB_HISTORY_TABLE = "NetskopeID-Accounts-History"
EMAIL_GSI = "EmailIndex"
EMAIL_ATTRIBUTE = "email"
HISTORY_WINDOW_DAYS = 30

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("ciam-database-agent")

# Posture Guard
ALLOWED_ACTIONS = frozenset({"dynamodb:Query", "dynamodb:GetItem"})

class PostureViolationError(RuntimeError):
    pass

def assert_posture(action: str) -> None:
    if action not in ALLOWED_ACTIONS:
        raise PostureViolationError(f"Posture violation: '{action}' not permitted. Allowed: {ALLOWED_ACTIONS}")

# Schemas
AccountStatusType = Literal["Customer", "Prospect - Net New", "Prospect - Churned", "Partner", "Former Customer"]
CustomerStatusType = Literal["Active", "Churned", "Inactive"]

class AccountRecord(BaseModel):
    account_name: str
    account_status: AccountStatusType
    customer_status: CustomerStatusType
    active_tenant_count: int
    tenant_url: Optional[str] = None
    sf_user_exists: bool
    sf_user_active: bool

class ChangeRecord(BaseModel):
    field_name: str
    old_value: str
    new_value: str
    changed_date: datetime
    changed_by: str

class DataFreshness(BaseModel):
    last_synced_at: Optional[datetime] = None
    age_hours: Optional[float] = None
    is_stale: bool = False

class AccountPayload(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    spec_id: Literal["SPEC-CIAM-0002"] = "SPEC-CIAM-0002"
    agent: Literal["ciam-database-agent"] = "ciam-database-agent"
    run_id: str
    fetched_at: datetime
    account_found: bool
    accounts: List[AccountRecord] = []
    recent_changes: List[ChangeRecord] = []
    history_fetch_error: Optional[str] = None
    data_freshness: DataFreshness
    data_warnings: List[str] = []
    error: Optional[str] = None

# DynamoDB Client
_dynamodb_client = None

def get_dynamodb_client():
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = boto3.client("dynamodb", region_name=AWS_REGION)
    return _dynamodb_client

# Tools
def get_account_by_email(email: str) -> tuple:
    assert_posture("dynamodb:Query")
    try:
        client = get_dynamodb_client()
        response = client.query(
            TableName=DYNAMODB_TABLE,
            IndexName=EMAIL_GSI,
            KeyConditionExpression=f"{EMAIL_ATTRIBUTE} = :email",
            ExpressionAttributeValues={":email": {"S": email}},
            ProjectionExpression="user_id, email, account_name, account_status, customer_status, active_tenant_count, tenant_url, sf_user_exists, sf_user_active",
        )
        items = response.get("Items", [])
        if not items:
            logger.info(f"No account found for email: {email}")
            return None, None
        
        accounts = []
        for item in items:
            account = AccountRecord(
                account_name=item.get("account_name", {}).get("S", ""),
                account_status=item.get("account_status", {}).get("S", "Customer"),
                customer_status=item.get("customer_status", {}).get("S", "Inactive"),
                active_tenant_count=int(item.get("active_tenant_count", {}).get("N", 0)),
                tenant_url=item.get("tenant_url", {}).get("S"),
                sf_user_exists=item.get("sf_user_exists", {}).get("BOOL", False),
                sf_user_active=item.get("sf_user_active", {}).get("BOOL", False),
            )
            accounts.append(account)
        logger.info(f"Found {len(accounts)} account(s) for email: {email}")
        return accounts, None
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(f"DynamoDB error: {error_code}")
        return None, error_code if error_code == "ProvisionedThroughputExceededException" else f"dynamodb_error: {error_code}"
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {e}")
        return None, f"query_error: {str(e)}"

def get_account_history(account_name: str) -> tuple:
    assert_posture("dynamodb:Query")
    try:
        client = get_dynamodb_client()
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=HISTORY_WINDOW_DAYS)
        cutoff_timestamp = thirty_days_ago.isoformat()
        
        response = client.query(
            TableName=DYNAMODB_HISTORY_TABLE,
            KeyConditionExpression="account_name = :name AND changed_date >= :cutoff",
            ExpressionAttributeValues={
                ":name": {"S": account_name},
                ":cutoff": {"S": cutoff_timestamp},
            },
        )
        items = response.get("Items", [])
        changes = [ChangeRecord(
            field_name=item.get("field_name", {}).get("S", ""),
            old_value=item.get("old_value", {}).get("S", ""),
            new_value=item.get("new_value", {}).get("S", ""),
            changed_date=datetime.fromisoformat(item.get("changed_date", {}).get("S", now.isoformat())),
            changed_by=item.get("changed_by", {}).get("S", "unknown"),
        ) for item in items]
        logger.info(f"Found {len(changes)} change(s) for {account_name}")
        return changes, None
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(f"History fetch failed: {error_code}")
        return [], error_code
    except Exception as e:
        logger.warning(f"History error: {type(e).__name__}")
        return [], type(e).__name__

# Helpers
def now_utc_iso() -> datetime:
    return datetime.now(timezone.utc)

def is_valid_email(email: str) -> bool:
    return email and "@" in email and len(email.strip()) > 2

def calculate_freshness(last_synced_at: Optional[datetime]) -> DataFreshness:
    if not last_synced_at:
        return DataFreshness()
    now = now_utc_iso()
    age = now - last_synced_at
    age_hours = age.total_seconds() / 3600
    return DataFreshness(last_synced_at=last_synced_at, age_hours=age_hours, is_stale=age_hours > 24)

# Main
app = BedrockAgentCoreApp()

@app.entrypoint
def fetch_account(payload: dict) -> dict:
    run_id = str(uuid.uuid4())
    fetched_at = now_utc_iso()
    data_warnings = []
    
    logger.info(f"[{run_id}] Agent 2 invoked. Keys: {list(payload.keys())}")
    
    raw_email = payload.get("email")
    email = raw_email.strip().lower() if isinstance(raw_email, str) else ""

    raw_account_name = payload.get("account_name")
    account_name = raw_account_name.strip() if isinstance(raw_account_name, str) else ""
    
    if not is_valid_email(email):
        logger.warning(f"[{run_id}] Invalid email: {email}")
        return AccountPayload(
            run_id=run_id,
            fetched_at=fetched_at,
            account_found=False,
            accounts=[],
            recent_changes=[],
            data_freshness=DataFreshness(),
            error="invalid_email_input",
        ).model_dump()
    
    logger.info(f"[{run_id}] Querying DynamoDB for email: {email}")
    accounts, tool1_error = get_account_by_email(email)
    
    if tool1_error:
        return AccountPayload(
            run_id=run_id,
            fetched_at=fetched_at,
            account_found=False,
            accounts=[],
            recent_changes=[],
            data_freshness=DataFreshness(),
            error=tool1_error,
        ).model_dump()
    
    if not accounts:
        logger.info(f"[{run_id}] No account found")
        return AccountPayload(
            run_id=run_id,
            fetched_at=fetched_at,
            account_found=False,
            accounts=[],
            recent_changes=[],
            data_freshness=DataFreshness(),
            error=None,
        ).model_dump()
    
    if len(accounts) > 1:
        data_warnings.append("multiple_accounts_found")
        logger.warning(f"[{run_id}] Found {len(accounts)} accounts")
    
    resolved_account_name = account_name or accounts[0].account_name
    logger.info(f"[{run_id}] Fetching history for {resolved_account_name}")
    recent_changes, history_error = get_account_history(resolved_account_name)
    
    freshness = calculate_freshness(fetched_at)
    if freshness.is_stale:
        data_warnings.append("data_may_be_stale")
    
    logger.info(f"[{run_id}] Done. account_found={len(accounts)>0} accounts={len(accounts)} changes={len(recent_changes)}")
    
    return AccountPayload(
        run_id=run_id,
        fetched_at=fetched_at,
        account_found=len(accounts) > 0,
        accounts=accounts,
        recent_changes=recent_changes,
        history_fetch_error=history_error,
        data_freshness=freshness,
        data_warnings=data_warnings,
        error=None,
    ).model_dump()

if __name__ == "__main__":
    app.run()
