import os
from censys.asm import AsmClient
from censys.common.exceptions import CensysException

## This uses https://github.com/0xmoot/s3sec to test for read, write, and delete permissions 
## https://rhinosecuritylabs.com/penetration-testing/penetration-testing-aws-storage/

api_key = os.environ('CENSYS_API_KEY')
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
                s3_buckets_url.append(f'https://{s3_buckets_name[4]}.s3.amazonaws.com')
        
        print(f"AWS S3 Exposed Buckets: {len(s3_buckets_url)}")

        file = open('urls.txt', 'w')
        for url in s3_buckets_url:
            file.write(url+"\n")
        file.close()

except CensysException as e:
    print(f"Error: {e}")
