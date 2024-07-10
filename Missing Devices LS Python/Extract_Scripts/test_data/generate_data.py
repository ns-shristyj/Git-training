from collections import defaultdict
import random
import pdb

# td_i = defaultdict(list)

# td_k = defaultdict(list)
# td_n = defaultdict(list)
# td_c = defaultdict(list)
# td_a = defaultdict(list)

Chars = [1,4,6,3,'T','F','P',"L","A","E",9,4,3,5,"D","W","Q"]


def main():

    td_i = defaultdict(list)

    for i in range(100):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Intune'].append({"serialNumber": serial, "Score":"CANI"})
        td_i['Crowdstrike'].append({"serial_number": serial, "last_seen": "2024-03-18T20:46:27Z", "Score":"CANI"})
        td_i['Netskope'].append({"host_info": {"serialNumber":serial}, "last_event": {"timestamp":1710797550},"Score":"CANI"})
        td_i['Automox'].append({"serial_number": serial, "last_refresh_time" : "2024-03-18T04:37:55+0000" ,"Score":"CANI"})


    for i in range(100):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Kandji'].append({"serial_number": serial, "Score":"CANK"})
        td_i['Crowdstrike'].append({"serial_number": serial, "last_seen": "2024-03-18T20:46:27Z","Score":"CANK"})
        td_i['Netskope'].append({"host_info": {"serialNumber":serial}, "last_event": {"timestamp":1710797550}, "Score":"CANK"})
        td_i['Automox'].append({"serial_number": serial, "last_refresh_time" : "2024-03-18T04:37:55+0000" , "Score":"CANK"})



    for i in range(10):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Kandji'].append({"serial_number": serial, "Score":"CAK"})
        td_i['Crowdstrike'].append({"serial_number": serial, "last_seen": "2024-03-18T20:46:27Z","Score":"CAK"})
        td_i['Automox'].append({"serial_number": serial, "last_refresh_time" : "2024-03-18T04:37:55+0000" , "Score":"CAK"})


    for i in range(10):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Kandji'].append({"serial_number": serial, "Score":"ANK"})
        td_i['Netskope'].append({"host_info": {"serialNumber":serial}, "last_event": {"timestamp":1710797550}, "Score":"ANK"})
        td_i['Automox'].append({"serial_number": serial, "last_refresh_time" : "2024-03-18T04:37:55+0000" , "Score":"ANK"})


    for i in range(10):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Kandji'].append({"serial_number": serial, "Score":"CNK"})
        td_i['Crowdstrike'].append({"serial_number": serial, "last_seen": "2024-03-18T20:46:27Z","Score":"CNK"})
        td_i['Netskope'].append({"host_info": {"serialNumber":serial}, "last_event": {"timestamp":1710797550},  "Score":"CNK"})



    # make test Intune users 
        
    for i in range(10):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Intune'].append({"serialNumber": serial, "Score":"CAI"})
        td_i['Crowdstrike'].append({"serial_number": serial, "last_seen": "2024-03-18T20:46:27Z", "Score":"CAI"})
        td_i['Automox'].append({"serial_number": serial, "last_refresh_time" : "2024-03-18T04:37:55+0000" ,"Score":"CAI"})


    for i in range(10):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Intune'].append({"serialNumber": serial, "Score":"ANI"})
        td_i['Netskope'].append({"host_info": {"serialNumber":serial}, "last_event": {"timestamp":1710797550}, "Score":"ANI"})
        td_i['Automox'].append({"serial_number": serial, "last_refresh_time" : "2024-03-18T04:37:55+0000" ,"Score":"ANI"})


    for i in range(10):
        serial = ""
        for i in range(1,10):
            serial += str(random.choice(Chars))

        
        td_i['Intune'].append({"serialNumber": serial, "Score":"CNI"})
        td_i['Crowdstrike'].append({"serial_number": serial, "last_seen": "2024-03-18T20:46:27Z","Score":"CNI"})
        td_i['Netskope'].append({"host_info": {"serialNumber":serial}, "last_event": {"timestamp":1710797550}, "Score":"CNI"})

    
    return td_i



if __name__ == '__main__':
    main()