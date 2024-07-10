from censys.asm import Risks # type: ignore
import json, requests, os # type: ignore

headers = {
    "Censys-Api-Key": os.getenv("CENSYS_API_KEY")
}
#get all gcp risk instances and write them into a json file called gcpRisks.json
def getGCPRisks():
    r = requests.get("https://app.censys.io/api/v2/risk-instances?includeHostData=true", headers=headers)
    data1 = r.json()

    file1 = open("gcpRisks.json","w")
    output = []
    for i in data1['risks']:
        type_id = i['typeID']
        if type_id == "gcp-storage-bucket-exposed":
            output.append(i)
    json.dump(output, file1, indent = 6)


#get urls/name of buckets from the gcp instances that getGCPRisks() retrieved
def getURLS():
    f = open("gcpRisks.json")
    data2 = json.load(f)
    file2 = open("gcpUrls.txt", "w")

    for i in data2:
        urlTail = i['context']['cri'].replace("cri:bucket:gcp:gcs:", '')
        # finalURL = "https://storage.googleapis.com/" + urlTail
        # file2.write(urlTail + " link: " + finalURL + "\n")
        file2.write(urlTail + "\n")

getGCPRisks()
getURLS()