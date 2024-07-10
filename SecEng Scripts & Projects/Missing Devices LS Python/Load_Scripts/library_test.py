from google.cloud import bigquery
import os 


GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_API_KEY']

projectId = 'ns-ciso-asa-automation'
client = bigquery.Client(project=projectId, client_options={'api_key': GOOGLE_APPLICATION_CREDENTIALS})