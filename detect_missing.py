import json 
from collections import defaultdict
import pdb
import os
from ts_kandji import main as tk
from ts_crowdkandji import main as tc
from ts_auto import main as auto_main
from ts_netskope import main as ns
from ts_intune import main as int_main

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

hermits = defaultdict(list)



kandji_data = tk()


crowdkandji = tc()

auto = auto_main()

nsd = ns()

intune = int_main()






kandji_string = str(kandji_data['Kandji'])
kandji_serials = []
for x in range(len(kandji_data['Kandji'])):
    kandji_serials.append(kandji_data['Kandji'][x]['serial_number'].lower().strip())

crowd_serials = []
for x in range(len(crowdkandji['Crowdstrike'])):
    crowd_serials.append(crowdkandji['Crowdstrike'][x]['serial_number'].lower().strip())

auto_serials = []
for x in range(len(auto['Automox'])):
    auto_serials.append(auto['Automox'][x]['serial_number'].lower().strip())

ns_serials = []
for x in range(len(nsd['Netskope'])):
    try:
        ns_serials.append(nsd['Netskope'][x]['host_info']['serialNumber'].lower().strip())
    except KeyError:
        ns_serials.append('N/A')




print('len kandji serials :', len(kandji_serials))
print('len intune serials :', len(intune['Intune']))
print('len crowd serials : ', len(crowd_serials))
print('len auto serials : ', len(auto_serials))
print('len ns serials : ', len(ns_serials))




def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append({'Inventory':sublist})


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)



    with open(output_json, 'a') as json_file:
        json_file.write(ldjson)
        json_file.write('\n')
        json_file.close()


def get_missing(mdm_source, stack_serials, mdm_keyname, serial_keyname, output_name):
    for kitem in mdm_source[mdm_keyname]:
        if not kitem[serial_keyname].lower().strip() in stack_serials:
            kitem['stack'] = output_name
            hermits[output_name].append(kitem)
            
            

output_json = BASE_DIR + '/missing/kandji_missing.json'
hermits = defaultdict(list)
get_missing(kandji_data, crowd_serials, 'Kandji', 'serial_number', 'Crowdstrike')
write_to_json(hermits, output_json)
hermits = defaultdict(list)
get_missing(kandji_data, auto_serials, 'Kandji', 'serial_number', 'Automox')
write_to_json(hermits, output_json)
hermits = defaultdict(list)
get_missing(kandji_data, ns_serials, 'Kandji', 'serial_number', 'Netskope')
write_to_json(hermits, output_json)

output_json = BASE_DIR + '/missing/intune_missing.json'
hermits = defaultdict(list)
get_missing(intune, crowd_serials, 'Intune', 'serialNumber', 'Crowdstrike')
write_to_json(hermits, output_json)
hermits = defaultdict(list)
get_missing(intune, auto_serials, 'Intune', 'serialNumber', 'Automox')
write_to_json(hermits, output_json)
hermits = defaultdict(list)
get_missing(intune, ns_serials, 'Intune', 'serialNumber', 'Netskope')

write_to_json(hermits, output_json)