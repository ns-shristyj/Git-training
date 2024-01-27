import os,csv,json
from collections import defaultdict




BASE_DIR = os.path.dirname(os.path.abspath(__file__))


data_root = '/in_data/'
# output_path = ''.join(BASE_DIR + '/out_data/data_inventory.csv')
output_dict = defaultdict(list)

def check_rows(rows):
    expected_length = 1
    new_rows = []
    count_sanatized = 0
    for row in rows:

        if len(row) != 1:
            print("ERROR: Data Dimentions are Not 1x1")
            exit()
        else:
            # get count of lower ones moved TODO
            new_rows.append(row[0].upper())

    return new_rows
            


def commit_to_inventory(data_files, stack_name):

    for i in range(len(data_files)):
        # get file to open
        file_path = ''.join(BASE_DIR + data_root + data_files[i])

        # get os 
        os_index = ['linux', 'mac', 'windows']
        os = os_index[i]
        # print(os)

        
    
        with open(file_path, 'r') as csv_file:
            reader = csv.reader(csv_file)
            header = next(reader)
            rows = list(reader)
            # 
            rows = check_rows(rows)
        
        for row in rows:
            output_dict[str(stack_name)].append([str(row), str(os)])



data_files = [
    'automox_linux_hostname.csv',
    'automox_mac_hostname.csv',
    'automox_windows_hostname.csv',
]

commit_to_inventory(data_files, 'automox')

data_files = [
    'crowdstrike_linux_hostname.csv',
    'crowdstrike_mac_hostname.csv',
    'crowdstrike_windows_hostname.csv',
]

commit_to_inventory(data_files, 'crowdstrike')


# Asset Inventory Loaded
print(output_dict.keys())


# output to json 

output_json = BASE_DIR + '/out_data/endpoint_asset_inventory.json'
with open(output_json, 'w') as json_file:
    json.dump(output_dict, json_file)





    

