from ts_intune import main as tk
from ts_auto import main as tc 

import os, json
from collections import defaultdict

import pdb


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


intune_automox = defaultdict(list)
outliers = defaultdict(list)

intune_devices = tk()
auto_devices = tc()

print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

orig_count_intune = len(intune_devices['Intune'])
orig_count_crowd  = len(auto_devices['Automox'])
print('Intune devices  ', orig_count_intune)
print('Automox devices   ', orig_count_crowd)
print('\n\n')



for kitem in intune_devices['Intune']:
    for citem in auto_devices['Automox']:
        if kitem['serialNumber'].lower() == citem['serial_number'].lower():
            # pdb.set_trace()
            if kitem not in intune_automox['AutoTune']: intune_automox['AutoTune'].append(kitem) # attempts to remove duplicates
            # intune_automox['AutoTune'].append(kitem) # attempts to remove duplicates
        else:
            # if citem not in outliers['Outliers']: outliers['Outliers'].append(citem)
            pass


print('\n-------------------------------------------')
print('-------------------------------------------------------------')
print('AutoTune   ', len(intune_automox['AutoTune']), '/', orig_count_intune)
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
        json_file.write('\n')
        json_file.close()


output_json = BASE_DIR + '/ts_output/autotune.json'

write_to_json(intune_automox, output_json)