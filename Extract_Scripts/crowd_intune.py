import requests,re,csv,json
from datetime import timedelta, datetime


import pdb
from collections import defaultdict


import os

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--normalize', help="Add Normalized logs, Output to appended Inventory", action='store_true')

args = parser.parse_args()

intune_client_id = os.environ['intune_client_id']
intune_client_secret = os.environ['intune_client_secret']


BASE_DIR = os.path.dirname(os.path.abspath(__file__))



intune_device = defaultdict(list)


def commit_to_inventory(data_files, stack_name):
        
        # os_index = ['linux', 'mac', 'windows']
        mi = ['deviceName', 'lastSyncDateTime', 'serialNumber', 'operatingSystem']
        for i in range(len(data_files['value'])):
            
            df = data_files['value'][i]
            # pdb.set_trace()
            
            
            values = {'hostname': str(df[mi[0]]), 'last_seen': str(df[mi[1]]),
                      'serial_number': str(df[mi[2]]),'OS': str(df[mi[3]]), 'stack': str(stack_name)}
            # print(values)
            if args.normalize:
                intune_device['Inventory'].append(values)
            else:
                intune_device['Inventory'].append(data_files['value'][i])
                



intune_api_url = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"

# OAuth configuration
scope = "https://graph.microsoft.com/.default"


def get_access_token(client_id, client_secret, scope):
    token_url = f"https://login.microsoftonline.com/3660eb39-46fc-424e-bdab-6df79b15db3c/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': intune_client_id,
        'client_secret': intune_client_secret,
        'scope': scope
    }
    response = requests.post(token_url, data=data)
    print(response.status_code)
    return response.json().get('access_token')


# Function to get devices from Intune API
def get_intune_devices(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json',
    }
    response = requests.get(intune_api_url, headers=headers)
    re = response.json()
  
    nextlink = re['@odata.nextLink']

    response = requests.get(nextlink, headers=headers)
    re2 = response.json()
    pdb.set_trace()
    return re, re2



def intune_devices():
    access_token = get_access_token(intune_client_id,intune_client_secret,scope)
    
    if access_token:
        devices_list = get_intune_devices(access_token)
        for devices in devices_list:
        
            if 'value' in devices:
                commit_to_inventory(devices, 'Intune')
            else:
                print('Error fetching devices:', devices)
    else:
        print('Error getting access token')


intune_devices()




def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            # pdb.set_trace()
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
    output_json = BASE_DIR + '/out_data/intune.json'

write_to_json(intune_device, output_json)