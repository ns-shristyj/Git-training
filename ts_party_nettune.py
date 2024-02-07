from ts_intune import main as tk
from ts_netskope import main as tc

import os, json
from collections import defaultdict

import pdb


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


intune_netskope = defaultdict(list)
outliers = defaultdict(list)

intune_devices = tk()
netskope_devices = tc()

print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

orig_count_intune = len(intune_devices['Intune'])
orig_count_netskope  = len(netskope_devices['Netskope'])
print('Intune devices  ', orig_count_intune)
print('Netskope devices   ', orig_count_netskope)
print('\n\n')



for kitem in intune_devices['Intune']:
    for citem in netskope_devices['Netskope']:

        try: 
            if kitem['serialNumber'].lower() == citem['host_info']['serialNumber'].lower():
                # pdb.set_trace()
                if kitem not in intune_netskope['NetTune']: intune_netskope['NetTune'].append(kitem) # attempts to remove duplicates
                # intune_netskope['NetTune'].append(kitem) # attempts to remove duplicates
            else:
                pass
                # outliers['Outliers'].append(citem)
        except KeyError:
            if citem not in outliers['Outliers']: outliers['Outliers'].append(citem)

print('\n-----------------------------------')
print('-------------------------------------------------------------')
print('NetTune   ', len(intune_netskope['NetTune']), '/', orig_count_intune)
print('Outliers   ', len(outliers['Outliers']))
print('-------------------------------------------------------------')
print('-----------------------------------\n')





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


output_json = BASE_DIR + '/ts_output/nettune.json'

write_to_json(intune_netskope, output_json)