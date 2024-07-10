import os
import shlex
import subprocess

# Open the list of website links that will be tested
address_list= []
cipher_list = [] 

with open('addresslist.txt') as file:
    for line in file:
        value = line.strip()
        address_list.append(str(value))

print(address_list)
file.close()

command = "echo | openssl s_client -connect " + address_list[0] + ":443 -tls1_2 -brief"

for i in address_list:
    output = subprocess.run(
                            command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    ssl_list = str(output).split("\\n")
    cipher_list.append(ssl_list[2])

for i in range(len(address_list)):
    print("The web address:", address_list[i], "and its", cipher_list[i])
