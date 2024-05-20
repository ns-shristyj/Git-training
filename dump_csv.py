import os
from google.cloud import storage

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the GCS bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    
    blob.upload_from_filename(source_file_name)

    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

if __name__ == "__main__":
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    source_file_name = "test.csv"
    destination_blob_name = "test.csv"

    upload_to_gcs(bucket_name, source_file_name, destination_blob_name)
