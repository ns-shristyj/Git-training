import json 
from collections import defaultdict
import pdb
import os
from ns_intune import main as int_main
import re


df = int_main()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


output = '/debug_intune/outputs'

# df = str(df)

mdm_serials = []
for item in df['Intune']:
    mdm_serials.append(item['serialNumber'].upper().strip())

print(mdm_serials)

for root, dirs, files in os.walk(BASE_DIR + output):
    for file in files:
        print(file)
        with open(BASE_DIR + output + '/' + file) as f:
            for line in f:
                # pdb.set_trace()
                for item in df['Intune']:
                    # pdb.set_trace()
                    if line.upper().strip() == item['serialNumber'].upper().strip():
                        
                        print(line)

                
                if not line.upper().strip() in mdm_serials:
                    print('Items not in serials')
                    print(line)
                   