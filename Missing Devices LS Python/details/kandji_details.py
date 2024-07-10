import os 
import requests


def getDevices(device_id):

    url = f'https://netskope.api.kandji.io/api/v1/devices/{device_id}/details'
    kandji_token = os.environ['kandji_token']
        
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(kandji_token)
    }
    response = requests.get(url, headers=headers)
    print(response.status_code)
    stats= response.status_code
    if stats == 200:
        results=response.json()

        return results
    else:
        print('some error')
        exit(1)



def getLocation(device_id):
    url = f'https://netskope.api.kandji.io/api/v1/devices/{device_id}/details/lostmode'

    kandji_token = os.environ['kandji_token']
        
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {}'.format(kandji_token)
    }
    response = requests.get(url, headers=headers)
    print(response.status_code)
    stats= response.status_code
    if stats == 200:
        results=response.json()

        return results
    else:
        print('some error')
        exit(1)