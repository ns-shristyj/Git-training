import json,os
from collections import defaultdict
import pdb

def get_unique(df):

    filtered_inventory = defaultdict(list)
    # print(len(df['intune']))

    # 
    c = 0
    for item in df['intune']:
        # if (item['manufacturer'].lower() == 'Dell Inc.'.lower() \
        # or item['manufacturer'].lower() == 'LENOVO'.lower()) \
        # and item['operatingSystem'].lower() == 'Windows'.lower():
            # print(item['operatingSystem'])
            # print(item['manufacturer'])
            # pdb.set_trace()
            filtered_inventory['Intune'].append(item)
    
    # print('inventory count  :', len(filtered_inventory['Intune']))
    

    return filtered_inventory


def main():

    input_file = 'Extract_Scripts/out_data/intune.json'

    intune_devices = defaultdict(list)

    with open(input_file, 'r') as f:
        for line in f:
            json_data = json.loads(line)
            intune_devices['intune'].append(json_data)

    inventory = get_unique(intune_devices)

    return inventory


    # print(intune_devices)


if __name__ == '__main__':
    main()