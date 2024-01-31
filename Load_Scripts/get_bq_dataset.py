import requests,os
import load_environ


BIGQUERY = os.environ['BIGQUERY']

method = 'GET'.upper()

projectId = ''
datasetId = ''

host = 'https://bigquery.googleapis.com'
uri = f'/bigquery/v2/projects/{projectId}/datasets/{datasetId}'

headers = {'Authorization': BIGQUERY}

r = requests.request(method, host+uri, headers=headers)
print(r.status_code)
print('---------\n\n')

json_response = r.json()


# enumerate datasets
print(json_response)

# for i in json_response['datasets']:
#     for k,v in i.items():
#         print(k,'  :  ',v)


