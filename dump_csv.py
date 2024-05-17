from googleapiclient import discovery
from oauth2client.client import GoogleCredentials

credentials = GoogleCredentials.get_application_default()
service = discovery.build('storage', 'v1', credentials=credentials)

filename = 'C:\\MyFiles\\sample.csv'
bucket = 'my_bucket'

body = {'name': 'dest_file_name.csv'}
req = service.objects().insert(bucket=bucket, body=body, media_body=filename)
resp = req.execute()