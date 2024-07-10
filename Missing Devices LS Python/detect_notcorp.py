import json 
from collections import defaultdict
import pdb
import os
from ns_flat_kandji import main as tk
from ns_crowdstrike import main as tc
from ns_auto import main as auto_main
from ns_netskope import main as ns
from ns_intune import main as int_main
from json_to_csv import  make_csv
from json_output import write_to_json
from time import strftime, localtime
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

notcorp = defaultdict(list)



kandji_data = tk()
crowdkandji = tc()
auto = auto_main()
nsd = ns()
intune = int_main()

mdm_serials = []

for i in range(len(kandji_data['Kandji'])):
    serial = kandji_data['Kandji'][i]['serial_number'].upper().strip()
    mdm_serials.append(serial)

print('kandji len  ',len(mdm_serials))

for i in range(len(intune['Intune'])):
    serial = intune['Intune'][i]['serialNumber'].upper().strip()
    mdm_serials.append(serial)

print('kandji len  ',len(mdm_serials))

crowd_serials = []
for x in range(len(crowdkandji['Crowdstrike'])):
    try:
        crowd_serials.append(crowdkandji['Crowdstrike'][x]['serial_number'].lower().strip())
    except KeyError:
        serial = 'No serial'
        crowd_serials.append(serial)

        pass

auto_serials = []
for x in range(len(auto['Automox'])):
    auto_serials.append(auto['Automox'][x]['serial_number'].lower().strip())

ns_serials = []
for x in range(len(nsd['Netskope'])):
    try:
        serial = nsd['Netskope'][x]['host_info']['serialNumber'].lower().strip()
        ns_serials.append(nsd['Netskope'][x]['host_info']['serialNumber'].lower().strip())
    except KeyError:
        serial = 'N/A'
        ns_serials.append(serial)


print('len MDM serials :', len(mdm_serials))
print('len crowd serials : ', len(crowd_serials))
print('len auto serials : ', len(auto_serials))
print('len ns serials : ', len(ns_serials))



def get_missing(mdm_source, stack_serials, output_name, channels):
    for i in range(len(stack_serials[output_name])):
        try:
            if len(channels)  == 2:
                serial = stack_serials[output_name][i][channels[0]][channels[1]]
                last_event = strftime('%Y-%m-%dT%H:%M:%S%z', localtime(stack_serials[output_name][i]['last_event']['timestamp']))
                last_seen = datetime.strptime(last_event, "%Y-%m-%dT%H:%M:%S%z")
                stack_serials[output_name][i]['last_seen_stack'] = str(last_seen.isoformat())
               
                 
         
            elif len(channels) == 1:
                serial = stack_serials[output_name][i][channels[0]]
        except KeyError:
            serial = 'N/A-N/A'

        # if serial == 'PW031Y99':
        #     print(stack_serials[output_name][i]['last_login_user'])
            # pdb.set_trace()
        if not serial.upper().strip() in mdm_source:
            # newdata = {"serial": serial.upper().strip(), 'stack': output_name}
            notcorp['Inventory'].append(stack_serials[output_name][i])



    # for kitem in mdm_source[mdm_keyname]:
    #     if not kitem[serial_keyname].lower().strip() in stack_serials:
    #         kitem['stack'] = output_name
    #         notcorp[output_name].append(kitem)


notcorp = defaultdict(list)
get_missing(mdm_serials, crowdkandji, 'Crowdstrike', ['serial_number'])
# print(notcorp['Inventory'])

# make_csv(notcorp,'crowdstrike', ['serial_number','last_login_user', 'last_seen', 'device_id', 'bios_manufacturer', 'bios_version', 'agent_version', 'external_ip', 'first_seen', 'mac_address'])

output_json = BASE_DIR + '/notcorp/nc_crowd.json'

write_to_json(notcorp, output_json)

# notcorp = defaultdict(list)
# get_missing(mdm_serials, crowd_serials, 'Crowdstrike')
# make_csv(notcorp,'crowdstrike')

# pdb.set_trace()
notcorp = defaultdict(list)
get_missing(mdm_serials, nsd, 'Netskope', ['host_info', 'serialNumber'])
output_json = BASE_DIR + '/notcorp/nc_netskope.json'
write_to_json(notcorp, output_json)





