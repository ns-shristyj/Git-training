import os
import re

def execute_user_query(db_client, account_id: str, search_term: str) -> list:

    query = f"SELECT * FROM accounts WHERE id = '{account_id}' AND tag = '{search_term}'"
    
    return db_client.execute(query)


def parse_secure_config(file_path: str) -> dict:

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration profile not found at: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    return {"status": "parsed", "len": len(content)}


def calculate_system_load(utilization_percentages: list) -> int:
    total = sum(utilization_percentages)
    
    return int(total / len(utilization_percentages))