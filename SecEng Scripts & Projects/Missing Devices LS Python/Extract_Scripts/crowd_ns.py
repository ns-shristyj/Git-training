import requests,re,csv,json
from datetime import timedelta, datetime


import pdb
from collections import defaultdict


import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-n', '--normalize', help="Add Normalized logs, Output to appended Inventory", action='store_true')

args = parser.parse_args()

ns_token = os.environ['ns_token']



BASE_DIR = os.path.dirname(os.path.abspath(__file__))




ns_devices = defaultdict(list)

def commit_to_inventory(data_files, stack_name):
        
        # os_index = ['linux', 'mac', 'windows']
        mi = ['hostname','timestamp','serialNumber','os']
        for i in range(len(data_files['data'])):
            df = data_files['data'][i]['attributes']
            try:
                serialNumber = str(df['host_info']['serialNumber'])
            except KeyError:
                serialNumber = 'N/A'

            values = {'hostname': str(df['host_info']['hostname']), 'last_seen': str(df['last_event']['timestamp']),
                      'serial_number': str(serialNumber),'OS': str(df['host_info']['os']), 'stack': str(stack_name)}
            # print(values)
            if args.normalize:
                ns_devices['Inventory'].append(values)
            else:
                # fixed _id duplicate problem in elk
                master_keys = ['client_install_time',
                                'client_version',     
                                'device_id',
                                'epdlp',
                                'gen_id',
                                'host_info',
                                'last_event',
                                'last_event_service_name',
                                'user_added_time',
                                'users']
                
                id_value = df['_id']
                df['gen_id'] = id_value
                del df['_id']
                ns_devices['Inventory'].append(df)




def get_ns():
    before = datetime.today() - timedelta(days=60)
    before_epoch = int(before.timestamp())
    todays_date = int(datetime.today().timestamp())
    url = "https://netskopecorp.goskope.com/api/v1/clients"
    og_query = f"(last_event.timestamp gte {before_epoch}) and (last_event.timestamp lte {todays_date})"
    params = {
        "token": f"{ns_token}",
        "query": f"{og_query}"
    }
    respo = requests.post(url, data=params)
    json_resp = respo.json()
    stats_code = respo.status_code
    print(stats_code)
    if json_resp['status'] == 'success':
         print('success')
         commit_to_inventory(json_resp, 'Netskope')
    
        
    

get_ns()



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
    
    output_json = BASE_DIR + '/out_data/netskope.json'

write_to_json(ns_devices, output_json)