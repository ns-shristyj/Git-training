# this script will create augmented_endpoint_asset_inventory replacing 'Inventory' with entry stackname. 


import json
import pdb
from collections import defaultdict
import os 
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input', help="input file to augment files", required=True, action='store')
parser.add_argument('-o', '--output', help="output file with MDM name to append to with categorizations by stack", required=True, action='store')
parser.add_argument('-s', '--stack', help="stack name", required=True, action='store')
args = parser.parse_args()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

file = BASE_DIR + '/ts_output/' + args.input

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

    stack = args.stack
    

    new_dict = json_data
    new_dict['Stack'] = stack
    

    augmented_data[str('Inventory')].append(new_dict)




def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append({key: sublist})
            


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    with open(output_json, 'a') as json_file:
        json_file.write(ldjson)
        json_file.write('\n')
        json_file.close()


output_json = BASE_DIR + '/volv_output/' + args.output

write_to_json(augmented_data, output_json)



    


  