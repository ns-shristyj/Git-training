import requests,re,csv,json
from datetime import timedelta, datetime
from falconpy import Hosts

import pdb
from collections import defaultdict
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--normalize', help="Add Normalized logs, Output to appended Inventory", action='store_true')

args = parser.parse_args()



import os

crowdstrike_client_id = os.environ['crowdstrike_client_id']
crowdstrike_client_secret = os.environ['crowdstrike_client_secret']



BASE_DIR = os.path.dirname(os.path.abspath(__file__))



crowdstrike_devices = defaultdict(list)



def commit_to_inventory(data_files, stack_name):

        # os_index = ['linux', 'mac', 'windows']
        master_keyset = ['hostname', 'last_seen', 'serial_number', 'platform_name', 
                         'product_type', 'connection_mac_address',
                         'product_type_desc','provision_status',
                         'platform_id', 'cid'
                         ]
        

        for item in data_files:

            try: 
                serialNumber = str(item['serial_number'])
            except KeyError:
                 serialNumber = 'N/A'

            try:
                hostname = str(item['hostname'])

            except KeyError:
                 hostname = 'N/A'

            values = {'hostname': hostname, 'last_seen': str(item['last_seen']),
                      'serial_number': serialNumber,'OS': str(item['platform_name']), 'stack': str(stack_name)}
            # print(values)
            # pdb.set_trace()
            if args.normalize:
                crowdstrike_devices['Inventory'].append(values)
            else:
                crowdstrike_devices['Inventory'].append(item)

def Crowdstrike_Devices():
    hosts = Hosts(client_id=crowdstrike_client_id, client_secret=crowdstrike_client_secret, pythonic=True) 
    limit = 5000 #limit 5000
    sort = "hostname"
    windows_criteria = "platform_name:'Windows'"
    other_filt = hosts.query_devices_by_filter_scroll(limit=limit, sort=sort)
    other_details = hosts.get_device_details(ids=other_filt.data)
    # pdb.set_trace()
    commit_to_inventory(other_details, 'Crowdstrike')


Crowdstrike_Devices()





def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            if args.normalize:
                json_data.append({key: sublist})
            else:
                json_data.append(sublist)



    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    # print(ldjson)


    # export 

    with open(output_json, 'a') as json_file:
        json_file.write(ldjson)

if args.normalize:
    output_json = BASE_DIR + '/out_data/full_endpoint_asset_inventory.json'
else:
    output_json = BASE_DIR + '/out_data/crowd.json'

write_to_json(crowdstrike_devices, output_json)