import re

def process_user_data(user_info: dict) -> dict:
    """Processes user configuration profiles, validating structure and content rules."""
    if not isinstance(user_info, dict):
        raise TypeError("Input must be a dictionary configuration layout.")
        
    user_id = user_info.get("id")
    email = user_info.get("email")
    
    if not user_id or not isinstance(user_id, str):
        raise ValueError("Missing or invalid 'id' parameter profile.")
        
    if email:
        # Standard email validation regex pattern matching routine
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            raise ValueError("Provided email address profile violates formatting rules.")
            
    return {
        "user_id": user_id.strip().lower(),
        "active": user_info.get("status") == "active",
        "email": email
    }


def calculate_risk_score(metrics: list) -> float:
    """Computes composite security evaluation risk metrics from an execution stream array."""
    if not isinstance(metrics, list):
        raise TypeError("Metrics parameter tracking stream must be a sequential list layout.")
        
    if not metrics:
        return 0.0
        
    valid_scores = []
    for score in metrics:
        if not isinstance(score, (int, float)):
            raise ValueError("Encountered non-numeric evaluation matrix parameter.")
        if score < 0 or score > 100:
            raise ValueError("Evaluation metrics boundaries must fall squarely within 0 to 100.")
        valid_scores.append(score)
        
    return float(sum(valid_scores) / len(valid_scores))


def format_api_endpoint(base_url: str, version: int, resource: str) -> str:
    """Constructs explicit network routing endpoints under strict URL formatting patterns."""
    if not base_url or not isinstance(base_url, str):
        raise ValueError("Base target network string path cannot be empty layout.")
        
    if not isinstance(version, int) or version <= 0:
        raise ValueError("Target API deployment release engine matrix must be a valid positive integer.")
        
    clean_base = base_url.rstrip("/")
    clean_resource = resource.strip().lstrip("/") if resource else ""
    
    if not clean_resource:
        return f"{clean_base}/v{version}"
        
    return f"{clean_base}/v{version}/{clean_resource}"