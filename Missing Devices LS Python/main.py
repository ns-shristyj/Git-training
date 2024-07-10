import subprocess

command = 'python ts_party.py -r'.split(' ')
subprocess.run(command)

command = 'python volv_loader.py'.split(' ')
subprocess.run(command)

command = 'python detect_missing.py'.split(' ')
subprocess.run(command)