import os
from censys.asm import AsmClient
from censys.common.exceptions import CensysException

# List containing buckets that are exceptions.
exception = [
    "adjmedia", "npa1-labbucket0-1sa9t6z6x7n2y", "netskope-pub-permalinks", "phishing-protection-demo",
    "summitnskp2023", "cackalack-pub", "npa1-labbucket1-1eab1ki8t924r", "ns3bucket", "mikeapp", "dlptestcw",
    "mediavision", "dapa", "aspimages", "vision-assets", "asp", "test-agency", "beckett-www", "pat-images",
    "netskopeclient", "agencyassets", "work-images", "island-production", "islandmedia", "images-compute",
    "npalab-labbucket1-1a3ll8czddwut", "npademo-labbucket0-ae2dliu76gc4", "netskopevgse-bucket1-1osvsyocm3guv",
    "netskopevgse-bucket1-z7yuo4z2ssrx", "cloudfront-lab-dgarrison", "totally-public-bucket01", "csw-labs",
    "nslab-labbucket1-1ej6dyro32ugu", "nslab-labbucket0-ugby3le454nd", "netskopevgse-bucket1-113wf2ov58464",
    "npademo-labbucket1-7gz3d7kt2lkd", "netskopevgsestasa-bucket1-1m6t287juqw8u", "open-and-empty", "netskopevgse-bucket1-13s9789y91gxc",
    "netskopevgse-bucket1-1ewoj4yavb9c0", "npalab-labbucket0-154yltt26pdc3", "jim-corporate", "2-2-8-s3-1681578156", "tvm-normal-bucket-test"
]

# Function to check if value is in the exception list
def check_list(name, exception):
    # Loop through the list to check if the exception is present
    for item in exception:
        if item == name:
            return True
        
    return False

api_key = os.getenv('CENSYS_API_TOKEN')
s3_buckets_url = []

severity_ranking = { "critical": 1, "high": 2, "medium": 3, "low": 4}

client = AsmClient(api_key)

assets = client.risks.get_risk_instances()

# Check the response status 
try:
    # Extract the name of the risks
    if 'risks' in assets:
        # Put values from API into a Dict
        risks_dict = {
            f"risk_{index + 1}": risk 
            for index, risk in enumerate(assets['risks'])
        }
        # Convert the dict to a list of tuples for sorting
        risks_list = list(risks_dict.items())
        # Sort the list by severity
        sorted_risks_list = sorted(risks_list, key=lambda x: severity_ranking.get(x[1].get('severity', ''), 5))
        # Convert the sorted list back to a dictionary
        sorted_risks_dict = {k: v for k, v in sorted_risks_list}

        for x in range(0, len(sorted_risks_dict)):
            if sorted_risks_dict[f"risk_{x + 1}"]["typeID"] == "aws-storage-bucket-exposed":
                s3_buckets_name = str(sorted_risks_dict[f"risk_{x + 1}"]["context"]["cri"]).split(":")
                if not check_list(s3_buckets_name[4], exception):
                            s3_buckets_url.append(f'https://{s3_buckets_name[4]}.s3.amazonaws.com')
        
        print(f"AWS S3 Exposed Buckets: {len(s3_buckets_url)}")

        file = open('urls.txt', 'w')
        for url in s3_buckets_url:
            file.write(url+"\n")
        file.close()

except CensysException as e:
    print(f"Error: {e}")