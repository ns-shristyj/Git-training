import requests,re,csv,json
from datetime import timedelta, datetime


import pdb
from collections import defaultdict


import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--normalize', help="Add Normalized logs, Output to appended Inventory", action='store_true')

args = parser.parse_args()

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
            if args.normalize:
                kandji_devices['Inventory'].append(values)
            else:
                kandji_devices['Inventory'].append(item)



def getDevices():
    devices=[]
    limit=300 # limit 300
    parameters = {"limit": limit}
    tot = 0
    bro = True
    
    
    while bro:
        url = "https://netskope.clients.us-1.kandji.io/api/v1/devices/"
        
        
        if tot > 0:
            parameters.update({"offset": f"{tot}"})
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {}'.format(kandji_token)
        }
        response = requests.get(url, headers=headers, params=parameters)
        print(response.status_code)
        stats= response.status_code
        if stats == 200:
            results=response.json()
            # pdb.set_trace()
            commit_to_inventory(results, 'Kandji')
            tot += len(results)

        if len(results) == 0:
            bro = False
            break
        
getDevices()


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
    output_json = BASE_DIR + '/out_data/kandji.json'

write_to_json(kandji_devices, output_json)