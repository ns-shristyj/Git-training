
# This script is to check full_endpoint_asset_inventory for newline errors.
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input', help='file to check for newline issues', action='store', required=True)
args = parser.parse_args()




with open(str(args.input), 'r') as f:
    inventory = f.readlines()

for line in inventory:
    line_integ = line.count('"Inventory"')
    # print(line_integ)
    if line_integ != 1:
        print("Line Error Found :", line)
        exit()


