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
  
    # print(len(df['netskope']))
    

    c = 0
    for item in df['netskope']:
        # c +=1  # debug 
        # print(c) # debug
        # pdb.set_trace()
      

        try:
            if (item['host_info']['device_make'].lower() == 'Dell Inc.'.lower() \
                or item['host_info']['device_make'].lower() == 'LENOVO'.lower() \
                    or item['host_info']['device_make'].lower() == 'Apple'.lower()):
                
            
                # print(item['system_manufacturer'])
                filtered_inventory['Netskope'].append(item)

        except KeyError:
            outlier['outliers'].append(item)


    
    # print('inventory count  :', len(filtered_inventory['Netskope']))
    # print('outlier count  :', len(outlier['outliers']))

    return filtered_inventory
   


def main():

    input_file = 'Extract_Scripts/out_data/netskope.json'

    netskope_devices = defaultdict(list)

    with open(input_file, 'r') as f:
        for line in f:
            json_data = json.loads(line)
            netskope_devices['netskope'].append(json_data)

    inventory = get_unique(netskope_devices)

    return inventory

    


if __name__ == '__main__':
    main()