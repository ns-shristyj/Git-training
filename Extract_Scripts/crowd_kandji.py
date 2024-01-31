import requests,re,csv,json
from datetime import timedelta, datetime
from falconpy import Hosts

import pdb
from collections import defaultdict


import os

kandji_token = os.environ['kandji_token']



BASE_DIR = os.path.dirname(os.path.abspath(__file__))



kandji_devices = defaultdict(list)

def commit_to_inventory(data_files, stack_name):

        # os_index = ['linux', 'mac', 'windows']
        mi = ['device_name', 'last_check_in', 'serial_number', 'platform', 'stack']
        for item in data_files:
            values = {'hostname': str(item[mi[0]]), 'last_seen': str(item[mi[1]]),
                      'serial_number': str(item[mi[2]]),'OS': str(item[mi[3]]), 'stack': str(stack_name)}
            # print(values)
            kandji_devices['Inventory'].append(values)



def getDevices():
    devices=[]
    limit=5
    url = "https://netskope.clients.us-1.kandji.io/api/v1/devices/"
    parameters = {"limit": limit}
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(kandji_token)
    }
    response = requests.get(url, headers=headers, params=parameters)
    print(response.status_code)
    stats= response.status_code
    if stats == 200:
        results=response.json()
        commit_to_inventory(results, 'Kandji')
        
        
getDevices()


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

write_to_json(kandji_devices, output_json)