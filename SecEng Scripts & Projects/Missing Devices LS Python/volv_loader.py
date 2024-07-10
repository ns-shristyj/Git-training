import os
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))



# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# if ERROR run -r reload first to load the data if it is missing.

try:
    subprocess.run(['python', f'{BASE_DIR}\\volv_load_aug2.py', '-i', 'crowdkandji.json', '-o', 'aug_kandji_2.json', '-s', 'Crowdstrike'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\volv_load_aug2.py', '-i', 'autokandji.json', '-o', 'aug_kandji_2.json', '-s', 'Automox'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\volv_load_aug2.py', '-i', 'netkandji.json', '-o', 'aug_kandji_2.json', '-s', 'Netskope'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\volv_load_aug2.py', '-i', 'crowdtune.json', '-o', 'aug_intune_2.json', '-s', 'Crowdstrike'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\volv_load_aug2.py', '-i', 'autotune.json', '-o', 'aug_intune_2.json', '-s', 'Automox'], shell=True, check=True)
    subprocess.run(['python', f'{BASE_DIR}\\volv_load_aug2.py', '-i', 'nettune.json', '-o', 'aug_intune_2.json', '-s', 'Netskope'], shell=True, check=True)


except subprocess.CalledProcessError:
    print('try to run script with -r if data is missing')