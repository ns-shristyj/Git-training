# this script keys keys and values from an index of crowdstrike endpoints

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
        key_nums.append(json_data)
  
        
samples = [0,-1, 15, 24,25,26,27]


# sa = 3087 #3087 has 59 keys


for sa in range(len(key_nums)):
    print('key numbers  :', len(key_nums[sa].keys()))

    if len(key_nums[sa].keys()) < 44:
        pdb.set_trace()

    # keys = []
    # for k,v in key_nums[sa].items():
    #     # pdb.set_trace()
    #     # newstr = str(k) + '  ' + str(v)
    #     keys.append(k)
    # # print('key Numbers :', len(keys))
    # # keys.sort()
    # for key in keys:
    #     print(key)
    # print('\n\n\n\n')



