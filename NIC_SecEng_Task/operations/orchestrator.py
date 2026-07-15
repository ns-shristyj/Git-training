# NIC_SecEng_Task/operations/orchestrator.py

from NIC_SecEng_Task.user_management.profile_service import ProfileService
from NIC_SecEng_Task.user_management.secure_gateway import SecureGateway

class UserOperationsOrchestrator:
    def __init__(self, db_client):
        self.profile_service = ProfileService(db_client)
        self.gateway = SecureGateway()

    def run_security_scan_and_update(self, user_id: str, payload: dict, system_log_path: str) -> dict:
        """
        Orchestrates an operation that updates a user profile and reads 
        associated system diagnostic logs.
        
        CRITICAL DEPENDENCY CHAIN:
        - Must mock the ProfileService responses safely.
        - Must pass inputs downstream to SecureGateway, exposing potential 
          cascading path traversal vulnerabilities if inputs aren't sanitized here.
        """
        # 1. Execute the functional profile update
        result = self.profile_service.process_user_data(user_id, payload)
        
        if result.get("status") == "error":
            return {"success": False, "stage": "profile_update", "error": result.get("message")}

        # 2. Consume the gateway to read a system file (Downstream vulnerability risk)
        try:
            # If the orchestrator blindly passes system_log_path without sanitizing it,
            # the path traversal flaw in secure_gateway.py gets triggered.
            log_data = self.gateway.read_user_file(system_log_path)
            return {
                "success": True,
                "profile": result.get("data"),
                "logs": log_data
            }
        except Exception as e:
            # Asserts how failures are caught when bad payloads bubble up
            return {
                "success": False,
                "stage": "log_reading",
                "error": f"Failed to retrieve logs safe: {str(e)}"
            }