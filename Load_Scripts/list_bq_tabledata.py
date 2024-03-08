import requests,os
import load_environ


BIGQUERY = os.environ['GOOGLE_API_KEY']

method = 'GET'.upper()

projectId = ''
datasetId = ''
tableId = ''

host = 'https://bigquery.googleapis.com'
uri = f'/bigquery/v2/projects/{projectId}/datasets/{datasetId}/tables/{tableId}/data'

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






