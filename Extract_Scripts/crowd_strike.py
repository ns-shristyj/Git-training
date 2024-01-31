import requests,re,csv,json
from datetime import timedelta, datetime
from falconpy import Hosts

import pdb
from collections import defaultdict


import os

crowdstrike_client_id = os.environ['crowdstrike_client_id']
crowdstrike_client_secret = os.environ['crowdstrike_client_secret']



BASE_DIR = os.path.dirname(os.path.abspath(__file__))



crowdstrike_devices = defaultdict(list)



def commit_to_inventory(data_files, stack_name):

        # os_index = ['linux', 'mac', 'windows']
        master_keyset = ['hostname', 'last_seen', 'serial_number', 'platform_name']
        

        for item in data_files:
            values = {'hostname': str(item['hostname']), 'last_seen': str(item['last_seen']),
                      'serial_number': str(item['serial_number']),'OS': str(item['platform_name']), 'stack': str(stack_name)}
            # print(values)
            crowdstrike_devices['Inventory'].append(values)

def Crowdstrike_Devices():
    hosts = Hosts(client_id=crowdstrike_client_id, client_secret=crowdstrike_client_secret, pythonic=True)
    limit = 3
    sort = "hostname"
    windows_criteria = "platform_name:'Windows'"
    other_filt = hosts.query_devices_by_filter_scroll(limit=limit, sort=sort)
    other_details = hosts.get_device_details(ids=other_filt.data)
    commit_to_inventory(other_details, 'Crowdstrike')


Crowdstrike_Devices()





def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append({key: sublist})


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    # print(ldjson)


    # export 

    with open(output_json, 'a') as json_file:
        json_file.write(ldjson)


output_json = BASE_DIR + '/out_data/full_endpoint_asset_inventory.json'

write_to_json(crowdstrike_devices, output_json)