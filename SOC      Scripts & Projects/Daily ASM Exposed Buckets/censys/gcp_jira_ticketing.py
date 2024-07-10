import requests
from requests.auth import HTTPBasicAuth
import json

readList = list()
writeList = list()
deleteList = list()
listList = list()
noneList = list()

f = open("gcpSecUrls.txt", "r")
lines = f.readlines()
for line in lines: 
    if "READ" in line:
        readList.append(line)
    elif "WRITE" in line:
        writeList.append(line)   
    elif "LIST" in line:
        listList.append(line)
    elif "DELETE" in line:
        deleteList.append(line)
    else:
        noneList.append(line)
        

# API KEY: ATATT3xFfGF0QhDj6Oy6CjZoIXd4y5WP2inLS5pRwnKmZqyNk2wA3BXvigpWAWJFkMXhRGyqX5RKq8aOv-I4n8AFm6ap9R0s2GjRUl5k6PTbf8n4oKreJhFDA4gTGc04_WWCee95mKMOdIFWcz4pasKAJTZBehua0NfADRoAZAUsINT92ByRiDY=AEE1CDD5

JIRA_URL = "https://netskope.atlassian.net"
SERVICEDESKID = 2
QUEUE_NAME = "Security Issues SOC"
PROJECT_KEY = 'TQI'


url = "https://netskope.atlassian.net/rest/servicedeskapi/request"

auth = HTTPBasicAuth("mangia@netskope.com", "ATATT3xFfGF0QhDj6Oy6CjZoIXd4y5WP2inLS5pRwnKmZqyNk2wA3BXvigpWAWJFkMXhRGyqX5RKq8aOv-I4n8AFm6ap9R0s2GjRUl5k6PTbf8n4oKreJhFDA4gTGc04_WWCee95mKMOdIFWcz4pasKAJTZBehua0NfADRoAZAUsINT92ByRiDY=AEE1CDD5")

headers = {
  "Accept": "application/json",
  "Content-Type": "application/json"
}

issue_data = {
    'serviceDeskId': 2,
    'requestTypeId': 36,
    'requestFieldValues': {
        'summary': "TESTING - Exposed GCP Buckets ASM",
        'description': f"{len(listList)} buckets are listable \n {len(readList)} buckets are readable \n {len(writeList)} buckets are writeable \n {len(deleteList)} buckets are deleteable \n {len(noneList)} exposed buckets exist but don't permit access"
    }
}



# Function to get the queue ID for the specified board
def get_queues():
    queues_url = f'{JIRA_URL}/rest/servicedeskapi/servicedesk/{SERVICEDESKID}/queue'
    response = requests.get(queues_url, headers=headers, auth=auth)
    if response.status_code == 200:
        return response.json()['values']
    return None


def create_issue():
    response = requests.post(
        url,
        data=json.dumps(issue_data),
        headers=headers,
        auth=auth
    )
    data = response.json()
    if response.status_code == 201:
        return data['issueKey']
    else:
        return False
    

def add_attachment(issueIdOrKey):
    url = f"https://netskope.atlassian.net/rest/api/2/issue/{issueIdOrKey}/attachments"
    headers = {
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check"
    }

    requests.post(
        url,
        headers = headers,
        auth = auth,
        files = {
            "file": ("gcpSecUrls.txt", open("gcpSecUrls.txt","rb"), "application-type")
        }
    )




# Main Script Execution 
queue_id = get_queues()
if queue_id:
    for queue in queue_id:
        if queue['name'] == QUEUE_NAME:
            queueUrl = f"https://netskope.atlassian.net/rest/servicedeskapi/servicedesk/2/queue/{queue['id']}"
            r = requests.get(queueUrl, headers=headers, auth=auth)

            queueData = r.json()
            f = open("test.json", "w")
            json.dump(queueData, f, indent = 4)

            issue_key = create_issue()
            if issue_key:
                print(f'Issue {issue_key} created successfully and will appear in queue "{QUEUE_NAME}" if it meets the JQL criteria.')
                add_attachment(issue_key)
                s = requests.get(f"https://netskope.atlassian.net/rest/servicedeskapi/request/{issue_key}",headers=headers, auth=auth)
                issueData = s.json()
                g = open("test.json", "w")
                json.dump(issueData, f, indent = 4)
            else:
                print('Failed to create issue.')
            break
    else:
        print(f'Project "{PROJECT_KEY}" is not a Jira Service Management project.')
else:
    print(f'Project with key "{PROJECT_KEY}" not found.')
