from ts_kandji import main as tk
from ts_crowdkandji import main as tc

import os, json
from collections import defaultdict

import pdb


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


kandji_crowd = defaultdict(list)
outliers = defaultdict(list)
hermits = defaultdict(list)

kandji_devices = tk()
crowd_devices = tc()

print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

orig_count_kandji = len(kandji_devices['Kandji'])
orig_count_crowd  = len(crowd_devices['Crowdstrike'])
print('kandji devices  ', orig_count_kandji)
print('crowd devices   ', orig_count_crowd)
print('\n\n')

for kitem in kandji_devices['Kandji']:
    for citem in crowd_devices['Crowdstrike']:
        if kitem['serial_number'].lower() == citem['serial_number'].lower():
            # pdb.set_trace()
            if kitem not in kandji_crowd['CrowdKandji']: kandji_crowd['CrowdKandji'].append(kitem) # attempts to remove duplicates
            # kandji_crowd['CrowdKandji'].append(kitem) # attempts to remove duplicates

        else:
            # if citem not in outliers['Outliers']: outliers['Outliers'].append(citem)
            pass

print('\n--------------------------------------------')
print('-------------------------------------------------------------')
print('Crowdkandji   ', len(kandji_crowd['CrowdKandji']), '/', orig_count_kandji)
print('Outliers   ', len(outliers['Outliers']))
print('-------------------------------------------------------------')
print('----------------------------------------------\n')





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


output_json = BASE_DIR + '/ts_output/crowdkandji.json'

write_to_json(kandji_crowd, output_json)

