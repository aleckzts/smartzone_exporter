import requests
import sys
import os
import urllib.parse
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

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
        r = requests.post(url, json=payload, headers=headers, verify=insecure)
    else:
        r = requests.get(url, headers=headers, verify=insecure)
    r.raise_for_status()
    return r.json()

def compare_dicts(baseline, other, prefix=''):
    diffs = []
    ignored_keys = {'id', 'zoneId', 'wlanId', 'createdTime', 'lastModifiedTime', 'schedule.id', 'firewallProfileId', 'portalServiceProfile.id', 'scheduler_config.id', 'scheduler_config.zoneId', 'schedule.name', 'portalServiceProfile.name', 'portal_config.id', 'portal_config.zoneId'}

    for key in baseline:
        path = f"{prefix}.{key}" if prefix else key
        if path in ignored_keys:
            continue
        if key not in other:
            diffs.append(f"{path} - só existe no baseline")
        elif isinstance(baseline[key], dict) and isinstance(other[key], dict):
            diffs.extend(compare_dicts(baseline[key], other[key], path))
        elif baseline[key] != other[key]:
            diffs.append(f"{path} - '{baseline[key]}' !== '{other[key]}'")

    for key in other:
        path = f"{prefix}.{key}" if prefix else key
        if path in ignored_keys:
            continue
        if key not in baseline:
            diffs.append(f"{path} - só existe no comparado")

    return diffs

def main():
    if len(sys.argv) == 4 and sys.argv[1] == "-z":
        mode = "zone"
        zones = [sys.argv[2], sys.argv[3]]
    elif len(sys.argv) == 5:
        mode = "ssid"
        zones = [sys.argv[1], sys.argv[3]]
        ssids = [sys.argv[2], sys.argv[4]]
    else:
        print("Uso: wificompare.py <zone1> <ssid1> <zona2> <ssid2>")
        print("Ou:  wificompare.py -z <zone1> <zona2>")
        sys.exit(1)

    user = os.environ['API_USER']
    password = os.environ['API_PASSWORD']
    target = os.environ['VSZ_TARGET']
    insecure = True

    if not all([target, user, password]):
        print("Defina as variáveis de ambiente VSZ_TARGET, API_USER e API_PASSWORD.")
        sys.exit(1)

    try:
        service_ticket = get_service_ticket(target, user, password, insecure)

        all_zones = get_data(target, 'system/inventory', service_ticket, insecure)['list']
        zones_id = []
        for zone_name in zones:
            zone = next((z for z in all_zones if z['zoneName'] == zone_name), None)
            if not zone:
                raise Exception(f"Zona '{zone_name}' não encontrada.")
            zones_id.append(zone['zoneId'])

        if mode == "ssid":
            wlans_id = []
            pos = 0
            for zone_id in zones_id:
                ssid_name = ssids[pos]
                wlans = get_data(target, f'rkszones/{zone_id}/wlans', service_ticket, insecure)['list']
                wlan = next((w for w in wlans if w['ssid'] == ssid_name), None)
                if not wlan:
                    raise Exception(f"SSID '{ssid_name}' não encontrado na zona '{zones[pos]}'.")
                wlans_id.append(wlan["id"])
                pos += 1

            baseline = f'{zones[0]}/{ssids[0]}'
            diff = f'{zones[1]}/{ssids[1]}'
            print(f"Buscando configuração de '{baseline}'...")
            config1 = get_data(target, f'rkszones/{zones_id[0]}/wlans/{wlans_id[0]}', service_ticket, insecure)
            if "id" in config1["schedule"] and config1["schedule"]["id"] != None:
                config1['scheduler_config'] = get_data(target, f'rkszones/{zones_id[0]}/wlanSchedulers/{config1["schedule"]["id"]}', service_ticket, insecure)
            if config1["portalServiceProfile"] != None:
                config1['portal_config'] = get_data(target, f'rkszones/{zones_id[0]}/portals/hotspot/{config1["portalServiceProfile"]["id"]}', service_ticket, insecure)
            print(f"Buscando configuração de '{diff}'...")
            config2 = get_data(target, f'rkszones/{zones_id[1]}/wlans/{wlans_id[1]}', service_ticket, insecure)
            if "id" in config2["schedule"] and config2["schedule"]["id"] != None:
                config2['scheduler_config'] = get_data(target, f'rkszones/{zones_id[1]}/wlanSchedulers/{config2["schedule"]["id"]}', service_ticket, insecure)
            if config2["portalServiceProfile"] != None:
                config2['portal_config'] = get_data(target, f'rkszones/{zones_id[1]}/portals/hotspot/{config2["portalServiceProfile"]["id"]}', service_ticket, insecure)
        else:
            baseline = f'{zones[0]}'
            diff = f'{zones[1]}'
            print(f"Buscando configuração de '{baseline}'...")
            config1 = get_data(target, f'rkszones/{zones_id[0]}', service_ticket, insecure)
            print(f"Buscando configuração de '{diff}'...")
            config2 = get_data(target, f'rkszones/{zones_id[1]}', service_ticket, insecure)

        print(f"\nComparando baseline '{baseline}' com '{diff}':\n")
        diffs = compare_dicts(config1, config2)
        if diffs:
            for d in diffs:
                print(" -", d)
        else:
            print("As configurações são idênticas.")
        print("")

    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


