import requests,re,csv,json
from datetime import timedelta, datetime
from falconpy import Hosts


crowdstrike_client_id = ''
crowdstrike_client_secret = ''
automox_api_key=''
kandji_token=''
ns_token=''
intune_client_id = ""
intune_client_secret = ""

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

    windows_csv_file_path = 'data/crowdstrike_windows_hostname.csv'
    mac_csv_file_path = 'data/crowdstrike_mac_hostname.csv'
    linux_csv_file_path = 'data/crowdstrike_linux_hostname.csv'

    with open(windows_csv_file_path, 'w', newline='') as windows_csvfile:
        windows_csv_writer = csv.writer(windows_csvfile)
        windows_csv_writer.writerow(['Windows'])
        for i in range(len(Windows_details)):
            windows_data = Windows_details[i]["hostname"]
            windows_csv_writer.writerow([windows_data])

    with open(mac_csv_file_path, 'w', newline='') as mac_csvfile:
        mac_csv_writer = csv.writer(mac_csvfile)
        mac_csv_writer.writerow(['Mac'])
        for i in range(len(mac_details)):
            mac_data = mac_details[i]["hostname"]
            mac_csv_writer.writerow([mac_data])

    with open(linux_csv_file_path, 'w', newline='') as linux_csvfile:
        linux_csv_writer = csv.writer(linux_csvfile)
        linux_csv_writer.writerow(['Linux'])
        for i in range(len(linux_details)):
            linux_data = linux_details[i]["hostname"]
            linux_csv_writer.writerow([linux_data])

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
    
    windows_csv_file_path = 'data/automox_windows_hostname.csv'
    mac_csv_file_path = 'data/automox_mac_hostname.csv'
    linux_csv_file_path = 'data/automox_linux_hostname.csv'
    
    windows_data = []
    mac_data = []
    linux_data = []
    
    for result in resu:
        server_name = result.get('name', '')
        os = result.get('os_family', '')
        if os == 'Windows':
            windows_data.append(server_name)
        elif os == 'Mac':
            mac_data.append(server_name)
        elif os == 'Linux':
            linux_data.append(server_name)
    
    with open(windows_csv_file_path, 'w', newline='') as windows_csvfile:
        windows_csv_writer = csv.writer(windows_csvfile)
        windows_csv_writer.writerow(['Windows'])
        for data in windows_data:
            windows_csv_writer.writerow([data])
    
    with open(mac_csv_file_path, 'w', newline='') as mac_csvfile:
        mac_csv_writer = csv.writer(mac_csvfile)
        mac_csv_writer.writerow(['Mac'])
        for data in mac_data:
            mac_csv_writer.writerow([data])
    
    with open(linux_csv_file_path, 'w', newline='') as linux_csvfile:
        linux_csv_writer = csv.writer(linux_csvfile)
        linux_csv_writer.writerow(['Linux'])
        for data in linux_data:
            linux_csv_writer.writerow([data])
    
    print('Total results: {}'.format(tot))
    print(f"CSV files created successfully: '{windows_csv_file_path}', '{mac_csv_file_path}', '{linux_csv_file_path}'")

Automox()



def createCSV(filename,objs):
    header_names=["hostname","serialNumber","os","user","email","lastSeen","installed","lastEnrolled","isMissing"]
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
                    devices.append([hostname,snumber,platformOS,user,email,lastConnect,installed,lastEnrolled,missing])
            if len(results) == 0:
                break
        if devices:
            createCSV('./kandjiDevices.csv',devices)
        else:
            print('no devices found')
            print(response.json())
            exit(1)
    else:
        print(response.json())
        print("unable to get results")
        
getDevices()



def create_csv_os(filename, objs):
    header_names = ['hostname', 'os']
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
    before = datetime.today() - timedelta(days=60)
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
                    if hostname and os_system:
                        hostname = hostname.upper()
                        res.append([hostname, os_system])
                except KeyError as ke:
                    pass
        else:
            print(json_resp)
        if len(res) > 0:
            os_set = set([os[1] for os in res])
            for os in os_set:
                os_res = [[hostname, os_system] for hostname, os_system in res if os_system == os]
                create_csv_os(f"./netskope_devices_{os}.csv", os_res)
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
        writer.writerow(["Device Name", "Email Address"])
        # Write data
        for device in devices:
            device_name = device.get("deviceName")
            email_address = device.get("emailAddress")
            writer.writerow([device_name, email_address])

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
