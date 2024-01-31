from google.cloud import bigquery
from google.cloud import storage
import os

# Replace with your own values
projectId = ''
datasetId = ''
tableId = ''
bucket_name = ''
file_path = 'endpoint_asset_inventory_hostname.json'


# Google Cloud Storage authentication
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_APPLICATION_CREDENTIALS']


storage_client = storage.Client(project=projectId)

# Initialize BigQuery and Storage clients
bq_client = bigquery.Client(project=projectId)
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
