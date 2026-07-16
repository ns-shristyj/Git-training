# NIC_SecEng_Task/user_management/profile_service.py

class ProfileService:
    def __init__(self, db_client):
        self.db = db_client

    def process_user_data(self, user_id: str, payload: dict) -> dict:
        """
        Processes user profile updates, validates account tiers, 
        and updates fields conditionally.
        """
        if not user_id or not isinstance(payload, dict):
            raise ValueError("Invalid input arguments")

        user = self.db.get_user(user_id)
        if not user:
            return {"status": "error", "message": "User not found"}

        # Logic Branch 1: Premium Tier Constraint
        if user.get("tier") == "premium":
            max_custom_fields = 10
        else:
            max_custom_fields = 3

        custom_fields = payload.get("custom_fields", {})
        if len(custom_fields) > max_custom_fields:
            return {"status": "error", "message": "Exceeded custom fields limit for account tier"}

        # Logic Branch 2: Soft deletion verification
        if user.get("is_deleted", False):
            return {"status": "error", "message": "Cannot update a deactivated account"}

        # Apply updates
        updated_profile = {
            "display_name": payload.get("display_name", user.get("display_name")),
            "custom_fields": custom_fields,
            "last_modified": "2026-07-15"
        }
        
        self.db.save_user(user_id, updated_profile)
        return {"status": "success", "data": updated_profile}