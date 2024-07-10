from ns_kandji import main as tk
from ns_crowdstrike import main as tc

import os, json
from collections import defaultdict
from write_outliers import write_to_json as write_outliers
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


    kandji_crowd = defaultdict(list)
    outliers = defaultdict(list)
    hermits = defaultdict(list)

    if not rt:
        kandji_devices = tk()
        crowd_devices = tc()
    else:
        from Extract_Scripts.test_data.generate_data import main as ts
        td_i = ts()
        kandji_devices = td_i
        crowd_devices = td_i

    print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

    orig_count_kandji = len(kandji_devices['Kandji'])
    orig_count_crowd  = len(crowd_devices['Crowdstrike'])
    print('kandji devices  ', orig_count_kandji)
    print('crowd devices   ', orig_count_crowd)
    print('\n\n')

    for kitem in kandji_devices['Kandji']:
        for citem in crowd_devices['Crowdstrike']:
            try:
                if kitem['serial_number'].lower().strip() == citem['serial_number'].lower().strip():
                    # pdb.set_trace()
                    if kitem not in kandji_crowd['CrowdKandji']: 
                        # pdb.set_trace()

                        last_seen = datetime.strptime(citem['last_seen'], "%Y-%m-%dT%H:%M:%SZ")
                        kitem['last_seen_stack'] = str(last_seen.isoformat())
                    

                        kandji_crowd['CrowdKandji'].append(kitem) # attempts to remove duplicates
                    # kandji_crowd['CrowdKandji'].append(kitem) # attempts to remove duplicates
            except KeyError:
                # pdb.set_trace()
                outliers['Outliers'].append(citem)
                citem['serial_number'] = 'NaNaN'


    print('\n--------------------------------------------')
    print('-------------------------------------------------------------')
    print('Crowdkandji   ', len(kandji_crowd['CrowdKandji']), '/', orig_count_kandji)
    print('Outliers   ', len(outliers['Outliers']))
    print('-------------------------------------------------------------')
    print('----------------------------------------------\n')






    output_json = BASE_DIR + '/ts_output/crowdkandji.json'

    if not rt:
        write_to_json(kandji_crowd, output_json)

        write_outliers(outliers, BASE_DIR + '/outliers/crowdstrike_outliers.json', 'device_id', 'No Serial Number in Crowdstrike')

    else:
        output_json = BASE_DIR + '/Extract_Scripts/test_data/tk.json'
        return kandji_crowd


if __name__ == '__main__':
    rt = False
    main(rt)