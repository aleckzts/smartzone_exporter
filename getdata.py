import requests
import sys
import os
import urllib.parse
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import json

# API version compatível
apiVersion = 'v11_1'

def get_service_ticket(target, user, password, insecure=False):
    if not insecure:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    session = requests.Session()
    r = session.post(f'{target}/wsg/api/public/{apiVersion}/serviceTicket',
                     json={'username': user, 'password': password},
                     verify=insecure)
    r.raise_for_status()
    return r.json().get('serviceTicket')

def get_data(target, path, service_ticket, insecure=False, payload=None):
    headers = {'Content-Type': 'application/json;charset=UTF-8'}
    url = f'{target}/wsg/api/public/{apiVersion}/{path}?serviceTicket={service_ticket}'
    if payload:
        r = requests.get(url, json=payload, headers=headers, verify=insecure)
    else:
        r = requests.get(url, headers=headers, verify=insecure)
    r.raise_for_status()
    return r.json()

def main():
    if len(sys.argv) != 2:
        print("Uso: getdata.py <path>")
        sys.exit(1)

    path = sys.argv[1]

    user = os.environ['API_USER']
    password = os.environ['API_PASSWORD']
    target = os.environ['VSZ_TARGET']

    insecure = True

    if not all([target, user, password]):
        print("Defina as variáveis de ambiente VSZ_TARGET, API_USER e API_PASSWORD.")
        sys.exit(1)

    try:
        service_ticket = get_service_ticket(target, user, password, insecure)

        raw = ''
        if 'query' in path:
            raw = {'page': 1, 'limit': 1000}

        data = get_data(target, path, service_ticket, insecure, raw)

        print(json.dumps(data, indent=4))
    except Exception as e:
        print(f"Erro ao obter dados: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

