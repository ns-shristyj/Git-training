import requests,re,csv,json
from datetime import timedelta, datetime


import pdb
from collections import defaultdict


import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--normalize', help="Add Normalized logs, Output to appended Inventory", action='store_true')

args = parser.parse_args()

automox_api_key = os.environ['automox_api_key']



BASE_DIR = os.path.dirname(os.path.abspath(__file__))




automox_devices = defaultdict(list)



def commit_to_inventory(data_files, stack_name):

        # os_index = ['linux', 'mac', 'windows']
        mi = ['name', 'last_refresh_time', 'serial_number', 'os_family']
        
        for item in data_files:
            values = {'hostname': str(item[mi[0]]), 'last_seen': str(item[mi[1]]),
                      'serial_number': str(item[mi[2]]),'OS': str(item[mi[3]]), 'stack': str(stack_name)}
            # print(values)
            if args.normalize:
                automox_devices['Inventory'].append(values)
            else:
                automox_devices['Inventory'].append(item)



def Automox():
    zx = automox_api_key
    ogs = 2553
    limit = 500 # 500 limit
    bro = True
    pg = 0
    tot = 0
    resu = []
    while bro:
        url = f"https://console.automox.com/api/servers?o={ogs}&page={pg}&limit={limit}"
        # pg += 1
        headrs = {
            'Authorization': 'Bearer {}'.format(zx)
        }
        response = requests.request("GET", url, headers=headrs)
        print(response.status_code)
        data = response.json()
        if len(data) <= 0: # limit stop
            bro = False
            break
        if response.status_code != 200:
            print('unable to get results')
            exit(1)
            break
        commit_to_inventory(data, 'Automox')
        pg += 1



Automox()



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
    output_json = BASE_DIR + '/out_data/automox.json'

write_to_json(automox_devices, output_json)