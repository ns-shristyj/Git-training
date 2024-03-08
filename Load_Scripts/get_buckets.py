import requests,os
import load_environ


BIGQUERY = os.environ['GOOGLE_API_KEY']

method = 'GET'.upper()

projectId = ''

host = 'https://storage.googleapis.com/storage/v1'
uri = f'/b?project={projectId}'

headers = {'Authorization': BIGQUERY}

r = requests.request(method, host+uri, headers=headers)
print(r.status_code)
print('---------\n\n')

json_response = r.json()

# print(json_response)

BUCKET = ''
for i in json_response['items']:
    for k,v in i.items():
        print(k,'  :  ',v)
        if k == 'name':
            BUCKET = v


uri = f'/b/{BUCKET}/o'

r = requests.request(method, host+uri, headers=headers)
print(r.status_code)
print('---------\n\n')

json_response = r.json()

# print(json_response)

for i in json_response['items']:
    for k,v in i.items():
        print(k,'  :  ',v)
   