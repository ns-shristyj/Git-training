import os
from google.cloud import storage

def upload_file_to_gcs(bucket_name, source_file_name,destination_blob_name):
  
    storage_client = storage.Client()
    
   
    bucket = storage_client.bucket(bucket_name)
    
    # blob = bucket.blob(test.csv)
    # blob.upload_from_filename(source_file_name)
    # print(f"File {source_file_name} uploaded to {destination_blob_name}.")
    # blob = bucket.blob(os.path.basename(source_file_name))
    

    # blob.upload_from_filename(source_file_name)
    
    # print(f"File {source_file_name} uploaded to {bucket_name} as {blob.name}.")
     
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")    

if __name__ == "__main__":
   
    bucket_name = "test-saas-bucket"
    source_file_name = "test.csv"
    destination_blob_name="test2.csv"
    upload_file_to_gcs(bucket_name, source_file_name,destination_blob_name)
