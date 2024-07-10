from censys.asm import Risks
import json, requests, os # type: ignore

api_key = os.getenv('CENSYS_API_TOKEN')

headers = {
    "Censys-Api-Key": f'{api_key}' #cycode_secret_ignore_here
}
output = []

#get all gcp risk instances and write them into a json file called gcpRisks.json
def getGCPRisks():
    r = requests.get("https://app.censys.io/api/v2/risk-instances?includeHostData=true", headers=headers)
    data1 = r.json()

    for i in data1['risks']:
        type_id = i['typeID']
        if type_id == "gcp-storage-bucket-exposed":
            output.append(i)


#get urls/name of buckets from the gcp instances that getGCPRisks() retrieved
def getURLS():
    file2 = open("gcpUrls.txt", "w")

    for i in output:
        urlTail = i['context']['cri'].replace("cri:bucket:gcp:gcs:", '')
        finalURL = "https://storage.googleapis.com/" + urlTail
        file2.write(urlTail + "\n")

getGCPRisks()
getURLS()
