import json,os,csv
from collections import defaultdict
import pdb
import requests
from details.kandji_details import getDevices


def write_to_csv():
    csv_output_path = 'ts_output/kandji.csv'

    return

def create_serial():

    return



def get_more(device_id):
    host = f"https://netskope.api.kandji.io/api/v1/devices/{device_id}/details"
    kandji_token = os.environ['kandji_token']




def get_unique(df):

    filtered_inventory = defaultdict(list)
  
    c = 0
    for item in df['kandji']:
       
        try:

            # if item['platform'].lower() == 'mac' and not item['user']['email'].startswith('ce-'):
            if not item['user']['email'].startswith('ce-'):
                
                device_id = item['device_id']
                # details = getDevices(device_id)
            
                # pdb.set_trace()
                filtered_inventory['Kandji'].append(item)
        except TypeError:
            #collect devices missing later
            pass
             

    return filtered_inventory



def main():

    input_file = 'Extract_Scripts/out_data/kandji.json'

    kandji_devices = defaultdict(list)

    with open(input_file, 'r') as f:
        for line in f:
            json_data = json.loads(line)
            kandji_devices['kandji'].append(json_data)

    inventory = get_unique(kandji_devices)
    

    return inventory



if __name__ == '__main__':
    main()