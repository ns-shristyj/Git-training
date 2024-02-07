# this script adds crowdstrike keys to a list if not already present in the list. Then returns those keys. 
# Example 68 total possible keys from crowdstrike reports

import json,os
from collections import defaultdict
import pdb

in_file = 'Extract_Scripts/out_data/crowd.json'
out_file = 'Extract_Scripts/out_data/crowd2.json'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

corrected_keys = defaultdict(list)


key_nums = []

with open(in_file, 'r') as f:
    for line in f.readlines():
        json_data = json.loads(str(line))
    
        for k,v in json_data.items():
            if not k in key_nums:
                key_nums.append(k)
        


print('total amount of keys in data: ', len(key_nums))

key_nums.sort()

for key in key_nums:
    print(key)
            


