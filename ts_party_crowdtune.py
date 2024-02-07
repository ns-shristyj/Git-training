from ts_intune import main as tk
from ts_crowdtune import main as tc

import os, json
from collections import defaultdict

import pdb


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


intune_crowd = defaultdict(list)
outliers = defaultdict(list)

intune_devices = tk()
crowd_devices = tc()

print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

orig_count_intune = len(intune_devices['Intune'])
orig_count_crowd  = len(crowd_devices['Crowdstrike'])
print('Intune devices  ', orig_count_intune)
print('Crowd devices   ', orig_count_crowd)
print('\n\n')



for kitem in intune_devices['Intune']:
    for citem in crowd_devices['Crowdstrike']:
        if kitem['serialNumber'].lower() == citem['serial_number'].lower():
            # pdb.set_trace()
            if kitem not in intune_crowd['CrowdTune']: intune_crowd['CrowdTune'].append(kitem) # attempts to remove duplicates
           
        else:
            # if citem not in outliers['Outliers']: outliers['Outliers'].append(citem)
            pass

print('\n-------------------------------------------------')
print('-------------------------------------------------------------')
print('CrowdTune   ', len(intune_crowd['CrowdTune']), '/', orig_count_intune)
print('Outliers   ', len(outliers['Outliers']))
print('-------------------------------------------------------------')
print('--------------------------------------------\n')





def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append(sublist)


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    # print(ldjson)


    # export 

    with open(output_json, 'a') as json_file:
        json_file.write(ldjson)


output_json = BASE_DIR + '/ts_output/crowdtune.json'

write_to_json(intune_crowd, output_json)