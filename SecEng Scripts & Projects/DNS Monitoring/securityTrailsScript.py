from requests.auth import HTTPBasicAuth # type: ignore
from datetime import date
from google.cloud import storage


import json
import requests # type: ignore
DOMAIN_NAME = "zscaler.net"

url = f"https://api.securitytrails.com/v1/domain/{DOMAIN_NAME}/subdomains?children_only=false&include_inactive=true"


headers = {
    "APIKEY": "21n26nEJ_XFzywPDEiHyj6SiumMRxE-9,
    "accept": "application/json"
}

def getDomains():
    r = requests.get(url=url, headers=headers)
    r = r.json()

    file = open("securityTrailsResults.json","w")
    json.dump(r, file, indent = 6)


    resultInfo = []
    domainName = r['subdomains'][0] + "." + DOMAIN_NAME
    url1 = f"https://api.securitytrails.com/v1/domain/{domainName}"
    n = requests.get(url=url, headers=headers)

    for i in r['subdomains']:
        domainName = i
        n = requests.get(f"https://api.securitytrails.com/v1/domain/{domainName}", headers=headers)
        nResult = n.json()
        resultInfo.append(nResult)
    
    file2 = open("securityTrailsResults2.json","w")
    json.dump(n, file2, indent = 6)    

getDomains()





# The ID of your GCS bucket
bucket_name = "dnsmonitoringbucket"

# The path to your file to upload
source_file_name = r"C:\Users\MayaAngia\Desktop\Domains\securityTrailsResults.json" #THIS NEEDS TO BE CHANGED OUT OF MY LOCAL PATH

# The ID of your GCS object
destination_blob_name = "zscalerSubdomains" + date.today().strftime("%Y%m%d")


def upload_blob(bucket_name, source_file_name, destination_blob_name):

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        f"File {source_file_name} uploaded to {destination_blob_name}."
    )

upload_blob(bucket_name, source_file_name, destination_blob_name)
