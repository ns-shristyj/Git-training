from ts_kandji import main as tk
from ts_netskope import main as tc 

import os, json
from collections import defaultdict

import pdb


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


kandji_netskope = defaultdict(list)
outliers = defaultdict(list)

kandji_devices = tk()
netskope_devices = tc()

print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

orig_count_kandji = len(kandji_devices['Kandji'])
orig_count_netskope  = len(netskope_devices['Netskope'])
print('Kandji devices  ', orig_count_kandji)
print('Netskope devices   ', orig_count_netskope)
print('\n\n')





for kitem in kandji_devices['Kandji']:
    for citem in netskope_devices['Netskope']:
        try:
            if kitem['serial_number'].lower() == citem['host_info']['serialNumber'].lower():
                # pdb.set_trace()
                if kitem not in kandji_netskope['NetKandji']: kandji_netskope['NetKandji'].append(kitem) # attempts to remove duplicates
                
            else:
                pass
                
        except KeyError:
            if citem not in outliers['Outliers']: outliers['Outliers'].append(citem)

print('\n-----------------------------------')
print('-------------------------------------------------------------')
print('NetKandji   ', len(kandji_netskope['NetKandji']), '/', orig_count_kandji)
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


output_json = BASE_DIR + '/ts_output/netkandji.json'

write_to_json(kandji_netskope, output_json)