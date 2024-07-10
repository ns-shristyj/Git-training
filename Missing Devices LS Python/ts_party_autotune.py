from ns_intune import main as tk
from ns_auto import main as tc 
from datetime import datetime
import os, json
from collections import defaultdict

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


    intune_automox = defaultdict(list)
    outliers = defaultdict(list)

    if not rt:
        intune_devices = tk()
        auto_devices = tc()
    else:
        from Extract_Scripts.test_data.generate_data import main as ts
        td_i = ts()
        intune_devices = td_i
        auto_devices = td_i
        # pdb.set_trace()

    print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

    orig_count_intune = len(intune_devices['Intune'])
    orig_count_crowd  = len(auto_devices['Automox'])
    print('Intune devices  ', orig_count_intune)
    print('Automox devices   ', orig_count_crowd)
    print('\n\n')



    for kitem in intune_devices['Intune']:
        for citem in auto_devices['Automox']:
            if kitem['serialNumber'].lower().strip() == citem['serial_number'].lower().strip():
                # pdb.set_trace()
                if kitem not in intune_automox['AutoTune']: 
                    try:
                        last_seen_datetime = datetime.strptime(citem['last_refresh_time'], "%Y-%m-%dT%H:%M:%S%z")
                        kitem['last_seen_stack'] = str(last_seen_datetime.isoformat())
                    except TypeError:
                        # pdb.set_trace()
                        # outlier
                        pass
                    intune_automox['AutoTune'].append(kitem) 
                    
                    # attempts to remove duplicates
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



    output_json = BASE_DIR + '/ts_output/autotune.json'

    if not rt:

        write_to_json(intune_automox, output_json)
    else:
        output_json = BASE_DIR + '/Extract_Scripts/test_data/tk.json'
        return intune_automox

if __name__ == '__main__':
    rt = False
    main(rt)