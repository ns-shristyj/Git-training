
# This script is to check full_endpoint_asset_inventory for newline errors.


with open('Extract_Scripts/out_data/full_endpoint_asset_inventory.json', 'r') as f:
    inventory = f.readlines()

for line in inventory:
    line_integ = line.count('"Inventory"')
    # print(line_integ)
    if line_integ != 1:
        print("Line Error Found :", line)
        exit()


