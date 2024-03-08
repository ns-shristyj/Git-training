from ts_kandji import main as tk
from ts_auto import main as tc 

import os, json
from collections import defaultdict

import pdb


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


kandji_automox = defaultdict(list)
outliers = defaultdict(list)

kandji_devices = tk()
auto_devices = tc()

print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

orig_count_kandji = len(kandji_devices['Kandji'])
orig_count_crowd  = len(auto_devices['Automox'])
print('kandji devices  ', orig_count_kandji)
print('Automox devices   ', orig_count_crowd)
print('\n\n')





for kitem in kandji_devices['Kandji']:
    for citem in auto_devices['Automox']:
        if kitem['serial_number'].lower() == citem['serial_number'].lower():
            # pdb.set_trace()
            if kitem not in kandji_automox['AutoKandji']: kandji_automox['AutoKandji'].append(kitem) # attempts to remove duplicates
            # kandji_automox['AutoKandji'].append(kitem) # attempts to remove duplicates
        else:
            # if citem not in outliers['Outliers']: outliers['Outliers'].append(citem)
            pass

print('\n-------------------------------------------')
print('-------------------------------------------------------------')
print('AutoKandji   ', len(kandji_automox['AutoKandji']), '/', orig_count_kandji)
print('Outliers   ', len(outliers['Outliers']))
print('-------------------------------------------------------------')
print('-----------------------------------------------\n')



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


output_json = BASE_DIR + '/ts_output/autokandji.json'

write_to_json(kandji_automox, output_json)