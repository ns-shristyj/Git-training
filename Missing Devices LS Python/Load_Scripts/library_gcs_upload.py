from google.cloud import storage
import os 



# Set up Google Cloud Storage authentication
GOOGLE_APPLICATION_CREDENTIALS = os.environ['GOOGLE_API_KEY']

def upload_file(bucket_name, source_file_path, destination_blob_name):
    # """Uploads a file to a Google Cloud Storage bucket."""

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_path)
    print(f"File {source_file_path} uploaded to {destination_blob_name} in {bucket_name}.")


bucket_name = ''
source_file_path = 'out_data/endpoint_asset_inventory_hostname.json'
destination_blob_name = 'endpoint_asset_inventory_hostname.json'

upload_file(bucket_name, source_file_path, destination_blob_name)
