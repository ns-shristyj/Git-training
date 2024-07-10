from google.cloud import bigquery
from google.cloud import storage
import os

# Replace with your own values
projectId = 'ns-ciso-asa-automation'
datasetId = 'dataset'
tableId = 'automation_table'
bucket_name = 'nightwagon'
file_path = 'intune.json'


# Google Cloud Storage authentication
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_API_KEY']



# Initialize BigQuery and Storage clients
bq_client = bigquery.Client(project=projectId, client_options={'api_key': GOOGLE_APPLICATION_CREDENTIALS})
storage_client = storage.Client(project=projectId)

# GCS path
gcs_uri = f'gs://{bucket_name}/{file_path}'


job_config = bigquery.LoadJobConfig(
    autodetect=True,  # Auto-detect schema from JSON file
    source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
)


# Start job
job = bq_client.load_table_from_uri(
    gcs_uri, f'{projectId}.{datasetId}.{tableId}', job_config=job_config
)

# Wait for the job to complete
job.result()

# Print the result
print(f'Table {tableId} created from {gcs_uri}')
