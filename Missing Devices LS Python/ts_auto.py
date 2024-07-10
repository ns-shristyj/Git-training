import json,os
from collections import defaultdict
import pdb


def write_to_debug(manu):
    out_file = 'ts_debug/crowd_manufacturers.txt'
    with open(out_file, 'a') as f:
        f.write(manu)
        f.write('\n')

def get_unique(df):
    filtered_inventory = defaultdict(list)
    outlier = defaultdict(list)
  
    # print(len(df['automox']))
    

    c = 0
    for item in df['automox']:
        # c +=1  # debug 
        # print(c) # debug
        # pdb.set_trace()
      

        try:
            if (item['detail']['VENDOR'].lower() == 'Dell Inc.'.lower() \
                or item['detail']['VENDOR'].lower() == 'LENOVO'.lower() \
                    or item['detail']['VENDOR'].lower() == 'Apple'.lower()):
                
            
                # print(item['system_manufacturer'])
                filtered_inventory['Automox'].append(item)

        except KeyError:
            outlier['outliers'].append(item)


    
    # print('inventory count  :', len(filtered_inventory['Automox']))
    # print('outlier count  :', len(outlier['outliers']))

    return filtered_inventory
   


def main():

    input_file = 'Extract_Scripts/out_data/automox.json'

    automox_devices = defaultdict(list)

    with open(input_file, 'r') as f:
        for line in f:
            json_data = json.loads(line)
            automox_devices['automox'].append(json_data)

    inventory = get_unique(automox_devices)

    return inventory

    


if __name__ == '__main__':
    main()