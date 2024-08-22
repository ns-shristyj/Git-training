import os
import json
import requests
from google.cloud import bigquery
from google.oauth2 import service_account
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Read the service account key from the environment variable
service_account_key = os.getenv('GCP_RSP_SERVICEACCOUNT_JSON')
if not service_account_key:
    raise ValueError("GCP_RSP_SERVICEACCOUNT_JSON environment variable is not set or is empty.")
else:
    print(f"Service account key is {len(service_account_key)} characters in length.")

service_account_info = json.loads(service_account_key)

service_account_info = json.loads(service_account_key)

# Create BigQuery credentials
credentials = service_account.Credentials.from_service_account_info(service_account_info)

# Initialize the BigQuery client with the credentials
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

datasets = list(client.list_datasets(project="research-special-programs"))
if datasets:
    print(f"Datasets in project:")
    for dataset in datasets:
        print(dataset.dataset_id)
else:
    print(f"No datasets found in project.")


# Define the query to fetch IP addresses (limited to 5 IPs from each table)
query = """
(SELECT ip_range FROM `research-special-programs.ds_prod.tbl_inventory_sub_all_ext` LIMIT 5)
"""

# Run the query and get the results
query_job = client.query(query)

# Fetch the results
results = query_job.result()

# Iterate through the results and print them
for row in results:
    print(f"{row.deviceId}")

sys.exit(0)

# Initialize an empty list to store IPs
ip_list = []

# Iterate over the results and add IPs to the list
for row in results:
    ip_list.append(row.ip_range)

# Function to fetch threat intelligence for IPs from Seclytics
def fetch_threat_intel_for_ips(ip_batch):
    url = "https://api.seclytics.com/ips"
    access_token = os.getenv("SECLYTICS_ACCESS_TOKEN")  # Read the access token from the environment variable

    params = {
        "access_token": access_token,
        "limit": 100,
        "fields": "whitelist,context",
        "ids": ",".join(ip_batch)  # Convert the list of IPs to a comma-separated string
    }

    try:
        response = requests.get(url, params=params)

        if response.status_code == 200:
            return response.json().get('data', [])
        else:
            logging.error(f"Failed to fetch data. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None

# Function to batch the IPs into chunks of 100
def batch_ips(ip_list, batch_size=100):
    for i in range(0, len(ip_list), batch_size):
        yield ip_list[i:i + batch_size]

def read_access_token(env_var):
    return os.getenv(env_var).strip()

def get_request_type_key(jira_url, jira_auth, service_desk_id):
    endpoint = f"{jira_url}/rest/servicedeskapi/servicedesk/{service_desk_id}/requesttype"
    response = requests.get(endpoint, auth=jira_auth, headers={'Content-Type': 'application/json'})

    if response.status_code == 200:
        request_types = response.json().get('values', [])
        for request_type in request_types:
            if request_type['name'] == "Security Issue":
                return request_type['id']
        raise Exception("Security Issue request type not found.")
    else:
        raise Exception(f"Failed to get request type key: {response.status_code}, {response.text}")

def create_jira_ticket(ip, context, categories, jira_url, jira_auth, project_key, request_type_key):
    reasons = context.get('reasons', {})
    source_urls = context.get('source_urls', {})

    summary = f"IP {ip} reported by Seclytics."

    # Mapping categories to URLs
    url_mapping = {
        "stopforumspam_ips": f"https://www.stopforumspam.com/ipcheck/{ip}",
        "blocklist_ua": f"https://blocklist.net.ua/check/?ip={ip}",
        "greensnow": f"https://greensnow.co/view/{ip}",
        "uceprotect_level1": "https://www.uceprotect.net/en/rblcheck.php",
        "uceprotect_level2": "https://www.uceprotect.net/en/rblcheck.php",
        "uceprotect_level3": "https://www.uceprotect.net/en/rblcheck.php",
        "dshield_daily_sources": f"https://www.dshield.org/ipinfo/{ip}"
    }

    # Collect all URLs for the categories present
    source_url_list = []
    for category in categories:
        if category in url_mapping:
            source_url_list.append(url_mapping[category])

    # Create a formatted string of source URLs
    source_urls_str = ", ".join(source_url_list)

    description = f"""
    IP {ip} flagged with threat intelligence data:
    
    * Reasons: {', '.join([f"{key}: {', '.join(values)}" for key, values in reasons.items()])}
    * Source URLs: {', '.join([f"{key}: {', '.join(urls)}" for key, urls in source_urls.items()])}
    * Categories: {', '.join(categories)}
    * Source URLs: {source_urls_str}
    """

    issue_data = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "GRC Security Issue"},
            "customfield_16362": [{"value": "SOC"}],
            "customfield_14800": request_type_key,
            "labels": ["security", "Security"]
        }
    }
    response = requests.post(f"{jira_url}/rest/api/2/issue", json=issue_data, auth=jira_auth)
    if response.status_code != 201:
        raise Exception(f"Failed to create Jira ticket: {response.status_code}, {response.text}")
    return response.json()['key']

def search_existing_tickets(ip, jira_url, jira_auth, project_key):
    jql = (
        f'project="{project_key}" AND summary~"{ip}" '
        f'AND created >= -7d AND issuetype="GRC Security Issue"'
    )
    search_url = f"{jira_url}/rest/api/2/search"
    params = {
        'jql': jql,
        'fields': 'key,summary,description'
    }
    response = requests.get(search_url, params=params, auth=jira_auth)
    if response.status_code != 200:
        raise Exception(f"Failed to search Jira tickets: {response.status_code}, {response.text}")

    issues = response.json().get('issues', [])
    return len(issues) > 0

def main():
    try:
        # Read the access token from environment variables
        token = read_access_token('SECLYTICS_ACCESS_TOKEN')

        # Read Jira details from environment variables
        jira_email = os.getenv('JIRA_EMAIL_HIMIL').strip()
        jira_token = os.getenv('JIRA_TOKEN_HIMIL').strip()
        jira_project_key = os.getenv('JIRA_PROJECT_KEY_HIMIL').strip()
        jira_auth = (jira_email, jira_token)

        # Hardcoded Jira URL and service desk ID
        jira_url = "https://netskope-sandbox.atlassian.net"
        service_desk_id = "TQI"

        # Get the request type key
        request_type_key = get_request_type_key(jira_url, jira_auth, service_desk_id)

        # Batch the IPs and process each batch
        for ip_batch in batch_ips(ip_list, batch_size=100):
            threat_data = fetch_threat_intel_for_ips(ip_batch)

            if threat_data:
                for ip_data in threat_data:
                    ip = ip_data.get('id')
                    context = ip_data.get('context', {})
                    categories = context.get('categories', [])

                    if categories:
                        # Check for existing tickets within the last week
                        if search_existing_tickets(ip, jira_url, jira_auth, jira_project_key):
                            logging.info(f"Jira ticket already exists for IP {ip} within the last week. Skipping ticket creation.")
                            continue

                        # Create Jira ticket for IP
                        jira_ticket = create_jira_ticket(ip, context, categories, jira_url, jira_auth, jira_project_key, request_type_key)
                        jira_ticket_url = f"{jira_url}/browse/{jira_ticket}"
                        logging.info(f"New Jira ticket created for IP {ip}: {jira_ticket_url}")

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
