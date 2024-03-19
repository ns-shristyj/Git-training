from ns_intune import main as tk
from ns_netskope import main as tc
from write_outliers import write_to_json as write_outliers
import os, json
from collections import defaultdict
from time import strftime, localtime
from datetime import datetime
import pdb


def write_to_json(output_dict, export_path):
    json_data = []
    for key, value in output_dict.items():
        for sublist in value:
            json_data.append(sublist)


    # Serialize the list of dictionaries to line-delimited JSON
    ldjson = '\n'.join(json.dumps(item) for item in json_data)


    # print(ldjson)


    # export 

    with open(export_path, 'a') as json_file:
        json_file.write(ldjson)
        json_file.write('\n')
        json_file.close()


def main(rt):

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


    intune_netskope = defaultdict(list)
    outliers = defaultdict(list)

    if not rt:
        intune_devices = tk()
        netskope_devices = tc()
    else:
        from Extract_Scripts.test_data.generate_data import main as ts
        td_i = ts()
        intune_devices = td_i
        netskope_devices = td_i

    print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

    orig_count_intune = len(intune_devices['Intune'])
    orig_count_netskope  = len(netskope_devices['Netskope'])
    print('Intune devices  ', orig_count_intune)
    print('Netskope devices   ', orig_count_netskope)
    print('\n\n')



    for kitem in intune_devices['Intune']:
        for citem in netskope_devices['Netskope']:

            try: 
                if kitem['serialNumber'].lower().strip() == citem['host_info']['serialNumber'].lower().strip():
                    # pdb.set_trace()
                    if kitem not in intune_netskope['NetTune']: 
                        last_event = strftime('%Y-%m-%dT%H:%M:%S%z', localtime(citem['last_event']['timestamp']))
                        last_seen = datetime.strptime(last_event, "%Y-%m-%dT%H:%M:%S%z")
                        kitem['last_seen_stack'] = str(last_seen.isoformat())
                        intune_netskope['NetTune'].append(kitem) # attempts to remove duplicates
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






    output_json = BASE_DIR + '/ts_output/nettune.json'

    if not rt:
        write_to_json(intune_netskope, output_json)
        write_outliers(outliers, BASE_DIR + '/outliers/netskope_outliers.json', 'device_id', 'No Serial Number in Netskope')
    else:
        return intune_netskope

if __name__ == '__main__':
    main()