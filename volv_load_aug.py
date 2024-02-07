# this script will create augmented_endpoint_asset_inventory replacing 'Inventory' with entry stackname. 


import json
import pdb
from collections import defaultdict
import os 


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

file = 'Extract_Scripts/out_data/full_endpoint_asset_inventory.json'

augmented_data = defaultdict(list)
# pdb.set_trace()

da = 0

with open(file, 'r') as f:
    rd = f.readlines()
print(len(rd))


for line in rd:
    try:
        json_data = json.loads(str(line))
    except json.decoder.JSONDecodeError:
        pdb.set_trace()

    stack = json_data['Inventory']['stack']
    dos = json_data['Inventory']['OS']
    if 'Linux'.lower() in dos.lower():
        dos = "Linux"
   
   
    new_dict = json_data['Inventory']
    new_dict['OS'] = dos

    augmented_data[stack].append(new_dict)




def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append({key: sublist})
            


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    with open(output_json, 'a') as json_file:
        json_file.write(ldjson)


output_json = BASE_DIR + '/Extract_Scripts/out_data/augmented_endpoint_asset_inventory.json'

write_to_json(augmented_data, output_json)



    


  