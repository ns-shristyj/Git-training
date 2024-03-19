from ns_kandji import main as tk
from ns_auto import main as tc 

import os, json
from collections import defaultdict
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


    kandji_automox = defaultdict(list)
    outliers = defaultdict(list)


    if not rt:
        kandji_devices = tk()
        auto_devices = tc()
    else:
        from Extract_Scripts.test_data.generate_data import main as ts
        td_i = ts()
        kandji_devices = td_i
        auto_devices = td_i
        # pdb.set_trace()
      

    print('---------------- loaded devices for transform operation ----------------\n\n\n\n')

    orig_count_kandji = len(kandji_devices['Kandji'])
    orig_count_crowd  = len(auto_devices['Automox'])
    print('kandji devices  ', orig_count_kandji)
    print('Automox devices   ', orig_count_crowd)
    print('\n\n')





    for kitem in kandji_devices['Kandji']:
        for citem in auto_devices['Automox']:
            if kitem['serial_number'].lower().strip() == citem['serial_number'].lower().strip():
                # pdb.set_trace()
                if kitem not in kandji_automox['AutoKandji']: 
                    # pdb.set_trace()
                    last_seen_datetime = datetime.strptime(citem['last_refresh_time'], "%Y-%m-%dT%H:%M:%S%z")
                    kitem['last_seen_stack'] = str(last_seen_datetime.isoformat())
                
                    kandji_automox['AutoKandji'].append(kitem) # attempts to remove duplicates
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



    output_json = BASE_DIR + '/ts_output/autokandji.json'

    if not rt:
     
        write_to_json(kandji_automox, output_json)
    else:
        output_json = BASE_DIR + '/Extract_Scripts/test_data/tk.json'
        # write_to_json(kandji_automox, output_json)
        return kandji_automox
        


if __name__ == '__main__':
    rt = False
    main(rt)