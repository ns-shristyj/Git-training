import requests, os, json # type: ignore
from requests.auth import HTTPBasicAuth # type: ignore
from dotenv import load_dotenv # type: ignore

# Load environment variables from .env file
load_dotenv()

# Jira Instance Details
JIRA_URL = os.environ.get('JIRA_URL')
USERNAME = os.getenv('JIRA_USERNAME')
API_TOKEN = os.getenv('JIRA_CQUINLAN_API_TOKEN')

# Project and queue details
PROJECT_KEY = 'TQI'
QUEUE_NAME = 'Security Issues SOC'
ISSUE_TYPE = 'GRC Security Issue'
SUMMARY = 'Daily ASM Buckets Exposed'
PROJECTID = '12594'
PROJECTNAME = 'Global Information Security Service Desk'
SERVICEDESKID = '2'
QUEUEID = '12'

# Project Variables
READ_LIST = []
WRITE_LIST = []
DELETE_LIST = []
ERROR_LIST = []
GCP_READ_LIST = []
GCP_WRITE_LIST = []
GCP_DELETE_LIST = []
GCP_LIST_LIST = []

file = open('s3status.txt', 'r')
lines = file.readlines()
for line in lines:
    split = line.split(" ")
    if 'read' in split[0] :
        READ_LIST.append(line)
    if 'write' in split[0] :
        WRITE_LIST.append(line)
    if 'delete' in split[0] :
        DELETE_LIST.append(line)
    if 'error' in split[0] :
        ERROR_LIST.append(line)
file.close()

gcp = open('gcpSecUrls.txt', 'r')
gcplines = gcp.readlines()
for line in lines: 
    if "READ" in line:
        GCP_READ_LIST.append(line)
    if "WRITE" in line:
        GCP_WRITE_LIST.append(line)   
    if "LIST" in line:
        GCP_LIST_LIST.append(line)
    if "DELETE" in line:
        GCP_DELETE_LIST.append(line)
gcp.close()

DESCRIPTION = f"""

*Issue Summary*

    This issue was created via automation that checks Censys ASM for any AWS S3 Buckets and GCP Buckets that are exposed to the public internet.

    
*S3 Bucket Status*

    There are currently {len(READ_LIST)} buckets are publicly readable.
    There are currently {len(WRITE_LIST)} buckets are publicly writable.
    There are currently {len(DELETE_LIST)} buckets are publicly deletable.
    There are currently {len(ERROR_LIST)} buckets have a error status.

*GCP Bucket Status*

    There are currently {len(GCP_READ_LIST)} buckets are publicly readable.
    There are currently {len(GCP_WRITE_LIST)} buckets are publicly writable.
    There are currently {len(GCP_DELETE_LIST)} buckets are publicly deletable.
    There are currently {len(GCP_LIST_LIST)} buckets have a error status.

    
*Additional Information*

For more details, visit:
 https://netskope.atlassian.net/wiki/spaces/ISI/pages/4516938819/BIS-Netskope+Information+Security+Playbook+-+AWS+S3+Buckets

"""

# Header Data
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Authentication
auth = HTTPBasicAuth(USERNAME,API_TOKEN)

# Function to get the queue ID for the specified board
def get_queues():
    queues_url = f'{JIRA_URL}/rest/servicedeskapi/servicedesk/{SERVICEDESKID}/queue'
    response = requests.get(queues_url, headers=headers, auth=auth)
    if response.status_code == 200:
        return response.json()['values']
    return None

# Create the issue in the specified project
def create_issue():
    create_issue_url = f'{JIRA_URL}/rest/servicedeskapi/request'
    issue_data = {
        'serviceDeskId': 2,
        'requestTypeId': 36,
        'requestFieldValues': {
            'summary': SUMMARY,
            'description': DESCRIPTION
        }
    }
    response = requests.post(create_issue_url, headers=headers, auth=auth, data=json.dumps(issue_data))
    if response.status_code == 201:

        issue_key = response.json()['issueKey']

        # If the ticket creation was successful, then assign the BIS Automation to the ticket
        ASSIGNcreate_issue_url = f'{JIRA_URL}/rest/api/3/issue/{issue_key}/assignee/'

        ASSIGNresponse = requests.put(ASSIGNcreate_issue_url,headers=headers,auth=auth, 
            data = json.dumps({'accountId': '60f9a9d656c7a70070ad8f07'}))
        
        if ASSIGNresponse:
            print(f"Assigned BIS Automation to ticket: {ASSIGNresponse}")

        # If the ticket creation was successful, then change the Security Scope to SOC
        SCOPEcreate_issue_url = f'{JIRA_URL}/rest/api/3/issue/{issue_key}'

        SCOPEissue_data = {
            'fields': {
                'customfield_16362': [
                    {
                        'value': 'SOC'
                    }
                ]
            }
        }

        SCOPEresponse = requests.request(
            "PUT",
            SCOPEcreate_issue_url, 
            headers=headers, 
            auth=auth, 
            data = json.dumps(SCOPEissue_data))
        
        if SCOPEresponse:
            print(f"Changed the SOC Scope of the ticket: {SCOPEresponse}")

        return issue_key
    else:
         print(f'Failed to create issue. Status code: {response.status_code}')
         print(f'Response: {response.text}')
    return None

def add_attachment(issue_key):
    add_attachment_url = f'{JIRA_URL}/rest/api/3/issue/{issue_key}/attachments'
    
    response = requests.post(
        add_attachment_url, 
        headers={'X-Atlassian-Token': 'no-check'}, 
        auth=auth, 
        files = {
            "file": ('S3 Bucket List', open('s3status.txt', 'rb'), "application-type"),
            "file": ('GCP Bucket List', open('gcpSecUrls.txt', 'rb'), "application-type")
        })
    
    if response.status_code == 200:
        print(f"Attachment has been added successfully to issue {issue_key}")
    else:
        print(f'Failed to add attachment. Status code: {response.status_code}')
        print(f'Response: {response.text}')


# Main Script Execution 
queue_id = get_queues()
if queue_id:
    for queue in queue_id:
        if queue['name'] == QUEUE_NAME:
            issue_key = create_issue()
            if issue_key:
                print(f'Issue {issue_key} created successfully and will appear in queue "{QUEUE_NAME}" if it meets the JQL criteria.')
                add_attachment(issue_key)
            else:
                print('Failed to create issue.')
            break
    else:
        print(f'Project "{PROJECT_KEY}" is not a Jira Service Management project.')
else:
    print(f'Project with key "{PROJECT_KEY}" not found.')