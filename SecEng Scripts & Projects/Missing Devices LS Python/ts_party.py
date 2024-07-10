import os
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('-r', '--reload', help="reloads json data from endpoints", action='store_true')
args = parser.parse_args()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if args.reload:
    subprocess.run(['python', f'{BASE_DIR}\\Extract_Scripts/crowd_control.py'])


# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# if ERROR run -r reload first to load the data if it is missing.

try:
    subprocess.run(['python', f'{BASE_DIR}\\ts_party_autokandji.py'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\ts_party_autotune.py'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\ts_party_crowdkandji.py'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\ts_party_crowdtune.py'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\ts_party_netkandji.py'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\ts_party_nettune.py'], shell=True, check=True)

except subprocess.CalledProcessError:
    print('try to run script with -r if data is missing')