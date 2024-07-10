import requests,re,csv,json
from datetime import timedelta, datetime, timezone, time
from falconpy import Hosts
import os
from datetime import datetime


crowdstrike_client_id = ''
crowdstrike_client_secret = ''
automox_api_key=''
kandji_token=''
ns_token=''
intune_client_id = ""
intune_client_secret = ""

def remove_extension(hostname):
    if hostname.count('.') == 3:  # Assuming IP address has 3 dots
        return hostname
    else:
        return hostname.split(".")[0]

def Crowdstrike_Devices():
    hosts = Hosts(client_id=crowdstrike_client_id, client_secret=crowdstrike_client_secret, pythonic=True)

    limit = 5000
    sort = "hostname"
    windows_criteria = "platform_name:'Windows'"
    mac_criteria = "platform_name:'Mac'"
    linux_criteria = "platform_name:'Linux'"

    wind_filt = hosts.query_devices_by_filter_scroll(limit=limit, filter=windows_criteria, sort=sort)
    mac_filt = hosts.query_devices_by_filter_scroll(limit=limit, filter=mac_criteria, sort=sort)
    linux_filt = hosts.query_devices_by_filter_scroll(limit=limit, filter=linux_criteria, sort=sort)

    Windows_details = hosts.get_device_details(ids=wind_filt.data)
    mac_details = hosts.get_device_details(ids=mac_filt.data)
    linux_details = hosts.get_device_details(ids=linux_filt.data)

    windows_csv_file_path = 'crowdstrike_windows_hostname.csv'
    mac_csv_file_path = 'crowdstrike_mac_hostname.csv'
    linux_csv_file_path = 'crowdstrike_linux_hostname.csv'

    one_week_ago = datetime.now() - timedelta(days=7)

    with open(windows_csv_file_path, 'w', newline='') as windows_csvfile:
        windows_csv_writer = csv.writer(windows_csvfile)
        windows_csv_writer.writerow(['Windows', 'Serial Number', 'Last Seen'])
        for i in range(len(Windows_details)):
            last_seen = datetime.strptime(Windows_details[i]["last_seen"], "%Y-%m-%dT%H:%M:%SZ")
            if last_seen >= one_week_ago:
                windows_data = remove_extension(Windows_details[i]["hostname"])
                if "serial_number" in Windows_details[i]:
                    serial_number = Windows_details[i]["serial_number"]
                    windows_csv_writer.writerow([windows_data, serial_number, last_seen])

    with open(mac_csv_file_path, 'w', newline='') as mac_csvfile:
        mac_csv_writer = csv.writer(mac_csvfile)
        mac_csv_writer.writerow(['Mac', 'Serial Number', 'Last Seen'])
        for i in range(len(mac_details)):
            last_seen = datetime.strptime(mac_details[i]["last_seen"], "%Y-%m-%dT%H:%M:%SZ")
            if "hostname" in mac_details[i]:
                if last_seen >= one_week_ago:
                    mac_data = remove_extension(mac_details[i]["hostname"])
                    serial_number = mac_details[i]["serial_number"]
                    mac_csv_writer.writerow([mac_data, serial_number, last_seen])
            else:
                print(f"No hostname found for device: {mac_details[i]}")
    with open(linux_csv_file_path, 'w', newline='') as linux_csvfile:
        linux_csv_writer = csv.writer(linux_csvfile)
        linux_csv_writer.writerow(['Linux', 'Serial Number', 'Last Seen'])
        for i in range(len(linux_details)):
            last_seen = datetime.strptime(linux_details[i]["last_seen"], "%Y-%m-%dT%H:%M:%SZ")
            if last_seen >= one_week_ago:
                linux_data = remove_extension(linux_details[i]["hostname"])
                if "serial_number" in linux_details[i]:
                    serial_number = linux_details[i]["serial_number"]
                    linux_csv_writer.writerow([linux_data, serial_number, last_seen])

    print(f"CSV files created successfully: '{windows_csv_file_path}', '{mac_csv_file_path}', '{linux_csv_file_path}'")

Crowdstrike_Devices()

def Automox():
    zx = automox_api_key
    ogs = 2553
    bro = True
    pg = 0
    tot = 0
    resu = []
    while bro:
        url = "https://console.automox.com/api/servers?o={}&page={}&limit=500".format(ogs, pg)
        pg += 1
        headrs = {
            'Authorization': 'Bearer {}'.format(zx)
        }
        response = requests.request("GET", url, headers=headrs)
        data = response.json()
        resu.extend(data)
        counts = len(data)
        tot += counts
        if counts <= 0:
            print('done getting results')
            break
        if response.status_code != 200:
            print('unable to get results')
            print(response.status_code)
            break
    
    windows_csv_file_path = 'automox_windows_hostname.csv'
    mac_csv_file_path = 'automox_mac_hostname.csv'
    linux_csv_file_path = 'automox_linux_hostname.csv'
    
    windows_data = []
    mac_data = []
    linux_data = []
    
    one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    
    for result in resu:
        server_name = result.get('name', '')
        os = result.get('os_family', '')
        serial_number = result.get('serial_number', '')
        last_seen = result.get('last_disconnect_time', '')
        if last_seen is None:
            last_seen = current_timestamp
            if os == 'Windows':
                    windows_data.append((server_name, serial_number, last_seen))
            elif os == 'Mac':
                    mac_data.append((server_name, serial_number, last_seen))
            elif os == 'Linux':
                    linux_data.append((server_name, serial_number, last_seen))
        else:
            last_seen_datetime = datetime.strptime(last_seen, "%Y-%m-%dT%H:%M:%S%z")
            if last_seen_datetime >= one_week_ago:
                if os == 'Windows':
                    windows_data.append((server_name, serial_number, last_seen))
                elif os == 'Mac':
                    mac_data.append((server_name, serial_number, last_seen))
                elif os == 'Linux':
                    linux_data.append((server_name, serial_number, last_seen))
    
    
    with open(windows_csv_file_path, 'w', newline='') as windows_csvfile:
        windows_csv_writer = csv.writer(windows_csvfile)
        windows_csv_writer.writerow(['Windows', 'Serial Number', 'Last Seen'])
        for data in windows_data:
            hostname = remove_extension(data[0])
            serial_number = data[1]
            last_seen = data[2]
            windows_csv_writer.writerow([hostname, serial_number, last_seen])
    
    with open(mac_csv_file_path, 'w', newline='') as mac_csvfile:
        mac_csv_writer = csv.writer(mac_csvfile)
        mac_csv_writer.writerow(['Mac', 'Serial Number', 'Last Seen'])
        for data in mac_data:
            hostname = remove_extension(data[0])
            serial_number = data[1]
            last_seen = data[2]
            mac_csv_writer.writerow([hostname, serial_number, last_seen])
    
    with open(linux_csv_file_path, 'w', newline='') as linux_csvfile:
        linux_csv_writer = csv.writer(linux_csvfile)
        linux_csv_writer.writerow(['Linux', 'Serial Number', 'Last Seen'])
        for data in linux_data:
            hostname = remove_extension(data[0])
            serial_number = data[1]
            last_seen = data[2]
            linux_csv_writer.writerow([hostname, serial_number, last_seen])
    
    print('Total results: {}'.format(tot))
    print(f"CSV files created successfully: '{windows_csv_file_path}', '{mac_csv_file_path}', '{linux_csv_file_path}'")

Automox()



def createCSV(filename, objs):
    header_names=["hostname","serialNumber","os","user","email","lastSeen","installed","lastEnrolled"]
    with open(filename,'w') as fn:
        rider= csv.writer(fn)
        rider.writerow(header_names)
        for i in objs:
            rider.writerow(i)

def getDevices():
    devices=[]
    limit=300
    url = "https://netskope.clients.us-1.kandji.io/api/v1/devices/"
    parameters = {"limit": limit}
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(kandji_token)
    }
    response = requests.get(url, headers=headers, params=parameters)
    print(response.status_code)
    stats= response.status_code
    if stats == 200:
        results=response.json()
        tot=limit
        for i in results:
            platformOS=i['platform']
            if platformOS == 'Mac':
                hostname=i['device_name']
                snumber=i['serial_number']
                user=i['user']
                if type(user) is dict:
                    user=i['user'].get('name')
                    email=i['user'].get('email')
                lastConnect=i['last_check_in']
                installed=i['agent_installed']
                lastEnrolled=i['last_enrollment']
                missing=i['is_missing']
                lastSeen = datetime.strptime(lastConnect, '%Y-%m-%dT%H:%M:%S.%fZ')
                if not user.startswith('CE-') and email != 'ce-infrastructure@netskope.com' and lastSeen >= datetime.now() - timedelta(days=7):
                    devices.append([hostname,snumber,platformOS,user,email,lastConnect,installed,lastEnrolled,missing])

        while True:
            parameters.update({"offset": f"{tot}"})
            response=requests.get(url, headers=headers, params=parameters)
            results=response.json()
            counts = len(results)
            tot += counts
            for i in results:
                platformOS=i.get('platform')
                if platformOS == 'Mac':
                    hostname=i.get('device_name')
                    snumber=i.get('serial_number')
                    user=i['user']
                    if type(user) is dict:
                        user=i['user'].get('name')
                        email=i['user'].get('email')
                    lastConnect=i.get('last_check_in')
                    installed=i.get('agent_installed')
                    lastEnrolled=i.get('last_enrollment')
                    missing=i.get('is_missing')
                    lastSeen = datetime.strptime(lastConnect, '%Y-%m-%dT%H:%M:%S.%fZ')
                    if not user.startswith('CE-Storage') and email != 'ce-infrastructure@netskope.com' and lastSeen >= datetime.now() - timedelta(days=7):
                        devices.append([hostname,snumber,platformOS,user,email,lastConnect,installed,lastEnrolled,missing])
            if len(results) == 0:
                break
        if devices:
            createCSV('kandjiDevices.csv',devices)
        else:
            print('no devices found')
            print(response.json())
            exit(1)
    else:
        print(response.json())
        print("unable to get results")
        
getDevices()



def create_csv_os(filename, objs):
    header_names = ['hostname', 'os','serial_number', 'last_seen']
    with open(filename, 'w') as fn:
        rider = csv.writer(fn)
        rider.writerow(header_names)
        for i in objs:
            rider.writerow(i)

def check_fields(field):
    if field:
        if len(field) > 1:
            field = field
        else:
            field = field[0]
    else:
        field = None
    return field

def get_ns():
    before = datetime.today() - timedelta(days=7)
    before_epoch = int(before.timestamp())
    todays_date = int(datetime.today().timestamp())
    url = "https://netskopecorp.goskope.com/api/v1/clients"
    params = {
        "token": f"{ns_token}",
        "query": f"(last_event.timestamp gte {before_epoch}) and (last_event.timestamp lte {todays_date})"
    }
    respo = requests.post(url, data=params)
    json_resp = respo.json()
    stats_code = respo.status_code
    if respo.status_code in (200, 205):
        res = []
        if 'error' not in json_resp['status']:
            for i in json_resp['data']:
                try:
                    atts = i['attributes']
                    host_info = atts['host_info']
                    hostname = host_info.get('hostname')
                    os_system = host_info.get('os')
                    serial_number = host_info.get('serialNumber')
                    last_seen = atts.get('last_event').get('timestamp')
                    if hostname and os_system and last_seen >= before_epoch:
                        hostname = hostname.upper()
                        res.append([hostname, os_system, serial_number, last_seen])
                except KeyError as ke:
                    pass
        else:
            print(json_resp)
        if len(res) > 0:
            os_set = set([os[1] for os in res])
            for os in os_set:
                os_res = [[hostname, os_system, serial_number, last_seen] for hostname, os_system, serial_number, last_seen in res if os_system == os]
                create_csv_os(f"netskope_devices_{os}.csv", os_res)
        else:
            print('no devices found')
            return
    else:
        print(stats_code)

get_ns()

intune_api_url = "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"

# OAuth configuration
scope = "https://graph.microsoft.com/.default"

# Function to authenticate and get OAuth token
def get_access_token(client_id, client_secret, scope):
    token_url = f"https://login.microsoftonline.com/3660eb39-46fc-424e-bdab-6df79b15db3c/oauth2/v2.0/token"
    data = {
        'grant_type': 'client_credentials',
        'client_id': intune_client_id,
        'client_secret': intune_client_secret,
        'scope': scope
    }
    response = requests.post(token_url, data=data)
    return response.json().get('access_token')

# Function to get devices from Intune API
def get_intune_devices(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(intune_api_url, headers=headers)
    return response.json()

# Function to write devices to CSV file
def write_to_csv(devices, csv_file):
    with open(csv_file, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Write header
        writer.writerow(["Device Name", "Email Address", "Serial Number", "Last Seen"])
        # Write data
        for device in devices:
            device_name = device.get("deviceName")
            email_address = device.get("emailAddress")
            serial_number = device.get("serialNumber")
            last_seen = device.get("lastSyncDateTime")
            last_seen_date = datetime.strptime(last_seen, "%Y-%m-%dT%H:%M:%S%z")
            one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            if last_seen_date >= one_week_ago:
                writer.writerow([device_name, email_address, serial_number, last_seen])

def intune_devices():
    access_token = get_access_token(intune_client_id,intune_client_secret,scope)
    
    if access_token:
        devices = get_intune_devices(access_token)
        
        if 'value' in devices:
            devices_list = devices['value']
            csv_file = 'intune_devices.csv'
            write_to_csv(devices_list, csv_file)
            print(f'Devices data written to {csv_file}')
        else:
            print('Error fetching devices:', devices)
    else:
        print('Error getting access token')

intune_devices()

def compare_kandji_crowdstrike():
    kandji_csv_file_path = 'kandjiDevices.csv'
    crowdstrike_csv_file_path = 'crowdstrike_mac_hostname.csv'
    missing_crowdstrike_file_path = 'missing_crowdstrike_devices(Mac).csv'

    kandji_devices = []
    crowdstrike_serials = set()

    # Read KandjiDevices CSV file
    with open(kandji_csv_file_path, 'r') as kandji_csvfile:
        kandji_csv_reader = csv.reader(kandji_csvfile)
        kandji_header = next(kandji_csv_reader)  # Get header row
        for row in kandji_csv_reader:
            kandji_devices.append(row)  # Add device row to list

    # Read Crowdstrike Mac CSV file
    with open(crowdstrike_csv_file_path, 'r') as crowdstrike_csvfile:
        crowdstrike_csv_reader = csv.reader(crowdstrike_csvfile)
        next(crowdstrike_csv_reader)  # Skip header row
        for row in crowdstrike_csv_reader:
            crowdstrike_serials.add(row[1].lower())  # Convert serial number to lowercase and add to set

    # Find missing Crowdstrike devices
    missing_crowdstrike_devices = []
    for device in kandji_devices:
        serial_number = device[1].lower()  # Assuming serial number is in the third column
        if serial_number not in crowdstrike_serials:
            missing_crowdstrike_devices.append(device)

    # Write missing Crowdstrike devices to file
    with open(missing_crowdstrike_file_path, 'w', newline='') as missing_crowdstrike_file:
        missing_crowdstrike_writer = csv.writer(missing_crowdstrike_file)
        missing_crowdstrike_writer.writerow(kandji_header)  # Write header row
        for device in missing_crowdstrike_devices:
            missing_crowdstrike_writer.writerow(device)

    print(f"Comparison completed. Missing Crowdstrike devices(Mac): {len(missing_crowdstrike_devices)}. "
          f"Files created: '{missing_crowdstrike_file_path}'")

compare_kandji_crowdstrike()

def compare_kandji_netskope():
    kandji_csv_file_path = 'kandjiDevices.csv'
    netskope_csv_file_path = 'netskope_devices_Mac.csv'
    missing_netskope_file_path = 'missing_netskope_devices(Mac).csv'

    kandji_devices = []
    netskope_serials = set()

    # Read KandjiDevices CSV file
    with open(kandji_csv_file_path, 'r') as kandji_csvfile:
        kandji_csv_reader = csv.reader(kandji_csvfile)
        kandji_header = next(kandji_csv_reader)  # Get header row
        for row in kandji_csv_reader:
            kandji_devices.append(row)  # Add device row to list

    # Read Netskope Devices CSV file
    with open(netskope_csv_file_path, 'r') as netskope_csvfile:
        netskope_csv_reader = csv.reader(netskope_csvfile)
        next(netskope_csv_reader)  # Skip header row
        for row in netskope_csv_reader:
            netskope_serials.add(row[2].lower())  # Convert serial number to lowercase and add to set

    # Find missing Netskope devices
    missing_netskope_devices = []
    for device in kandji_devices:
        serial_number = device[1].lower()  # Assuming serial number is in the second column
        if serial_number not in netskope_serials:
            missing_netskope_devices.append(device)

    # Write missing Netskope devices to file
    with open(missing_netskope_file_path, 'w', newline='') as missing_netskope_file:
        missing_netskope_writer = csv.writer(missing_netskope_file)
        missing_netskope_writer.writerow(kandji_header)  # Write header row
        for device in missing_netskope_devices:
            missing_netskope_writer.writerow(device)

    print(f"Comparison completed. Missing Netskope devices(Mac): {len(missing_netskope_devices)}. "
          f"Files created: '{missing_netskope_file_path}'")

compare_kandji_netskope()

def compare_kandji_automox():
    kandji_csv_file_path = 'kandjiDevices.csv'
    automox_csv_file_path = 'automox_mac_hostname.csv'
    missing_automox_file_path = 'missing_automox_devices(Mac).csv'

    kandji_devices = []
    automox_serials = set()

    # Read KandjiDevices CSV file
    with open(kandji_csv_file_path, 'r') as kandji_csvfile:
        kandji_csv_reader = csv.reader(kandji_csvfile)
        kandji_header = next(kandji_csv_reader)  # Get header row
        for row in kandji_csv_reader:
            kandji_devices.append(row)  # Add device row to list

    # Read Automox serial CSV file
    with open(automox_csv_file_path, 'r') as automox_csvfile:
        automox_csv_reader = csv.reader(automox_csvfile)
        next(automox_csv_reader)  # Skip header row
        for row in automox_csv_reader:
            automox_serials.add(row[1].lower())  # Convert serial number to lowercase and add to set

    # Find missing Automox devices
    missing_automox_devices = []
    for device in kandji_devices:
        serial_number = device[1].lower()  # Assuming serial number is in the second column
        if serial_number not in automox_serials:
            missing_automox_devices.append(device)

    # Write missing Automox devices to file
    with open(missing_automox_file_path, 'w', newline='') as missing_automox_file:
        missing_automox_writer = csv.writer(missing_automox_file)
        missing_automox_writer.writerow(kandji_header)  # Write header row
        for device in missing_automox_devices:
            missing_automox_writer.writerow(device)

    print(f"Comparison completed. Missing Automox devices(Mac): {len(missing_automox_devices)}. "
          f"Files created: '{missing_automox_file_path}'")

compare_kandji_automox()

def compare_intune_crowdstrike():
    intune_csv_file_path = 'intune_devices.csv'
    crowdstrike_csv_file_path = 'crowdstrike_windows_hostname.csv'
    missing_crowdstrike_file_path = 'missing_crowdstrike_devices(Windows).csv'
    intune_serials = set()
    crowdstrike_serials = set()

    # Read intune_devices CSV file
    with open(intune_csv_file_path, 'r') as intune_csvfile:
        intune_csv_reader = csv.reader(intune_csvfile)
        next(intune_csv_reader)  # Skip header row
        for row in intune_csv_reader:
            intune_serials.add(row[2].lower())  # Convert serial number to lowercase and add to set

    # Read Crowdstrike Windows serial CSV file
    with open(crowdstrike_csv_file_path, 'r') as crowdstrike_csvfile:
        crowdstrike_csv_reader = csv.reader(crowdstrike_csvfile)
        next(crowdstrike_csv_reader)  # Skip header row
        for row in crowdstrike_csv_reader:
            crowdstrike_serials.add(row[1].lower())  # Convert serial number to lowercase and add to set

    # Find missing Crowdstrike devices
    missing_crowdstrike_serials = intune_serials - crowdstrike_serials

    # Write missing Crowdstrike devices to file
    with open(missing_crowdstrike_file_path, 'w', newline='') as missing_crowdstrike_file:
        missing_crowdstrike_writer = csv.writer(missing_crowdstrike_file)
        missing_crowdstrike_writer.writerow(['Missing Crowdstrike Serials'])
        for serial_number in missing_crowdstrike_serials:
            missing_crowdstrike_writer.writerow([serial_number])

    print(f"Comparison completed. Missing Crowdstrike devices(Windows): {len(missing_crowdstrike_serials)}. "
          f"Files created: '{missing_crowdstrike_file_path}'")

compare_intune_crowdstrike()

def compare_intune_automox():
    intune_csv_file_path = 'intune_devices.csv'
    automox_csv_file_path = 'automox_windows_hostname.csv'
    missing_automox_file_path = 'missing_automox_devices(Windows).csv'

    intune_serials = set()
    automox_serials = set()

    # Read intune_devices CSV file
    with open(intune_csv_file_path, 'r') as intune_csvfile:
        intune_csv_reader = csv.reader(intune_csvfile)
        next(intune_csv_reader)  # Skip header row
        for row in intune_csv_reader:
            intune_serials.add(row[2].lower())  # Convert serial number to lowercase and add to set

    # Read Automox Windows serial CSV file
    with open(automox_csv_file_path, 'r') as automox_csvfile:
        automox_csv_reader = csv.reader(automox_csvfile)
        next(automox_csv_reader)  # Skip header row
        for row in automox_csv_reader:
            automox_serials.add(row[1].lower())  # Convert serial number to lowercase and add to set

    # Find missing Automox devices
    missing_automox_serials = intune_serials - automox_serials

    # Write missing Automox devices to file
    with open(missing_automox_file_path, 'w', newline='') as missing_automox_file:
        missing_automox_writer = csv.writer(missing_automox_file)
        missing_automox_writer.writerow(['Missing Automox Serials'])
        for serial_number in missing_automox_serials:
            missing_automox_writer.writerow([serial_number])

    print(f"Comparison completed. Missing Automox devices(Windows): {len(missing_automox_serials)}. "
          f"Files created: '{missing_automox_file_path}'")

compare_intune_automox()

def compare_intune_netskope():
    intune_csv_file_path = 'intune_devices.csv'
    netskope_csv_file_path = 'netskope_devices_Windows.csv'
    missing_netskope_file_path = 'missing_netskope_devices(Windows).csv'
    intune_serials = set()
    netskope_serials = set()

    # Read intune_devices CSV file
    with open(intune_csv_file_path, 'r') as intune_csvfile:
        intune_csv_reader = csv.reader(intune_csvfile)
        next(intune_csv_reader)  # Skip header row
        for row in intune_csv_reader:
            intune_serials.add(row[2].lower())  # Convert serial number to lowercase and add to set

    # Read Netskope Windows serial CSV file
    with open(netskope_csv_file_path, 'r') as netskope_csvfile:
        netskope_csv_reader = csv.reader(netskope_csvfile)
        next(netskope_csv_reader)  # Skip header row
        for row in netskope_csv_reader:
            netskope_serials.add(row[2].lower())  # Convert serial number to lowercase and add to set

    # Find missing Netskope devices
    missing_netskope_serials = intune_serials - netskope_serials

    # Write missing Netskope devices to file
    with open(missing_netskope_file_path, 'w', newline='') as missing_netskope_file:
        missing_netskope_writer = csv.writer(missing_netskope_file)
        missing_netskope_writer.writerow(['Missing Netskope Serials'])
        for serial_number in missing_netskope_serials:
            missing_netskope_writer.writerow([serial_number])

    print(f"Comparison completed. Missing Netskope devices(Windows): {len(missing_netskope_serials)}. "
          f"Files created: '{missing_netskope_file_path}'")

compare_intune_netskope()
