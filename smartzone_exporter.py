# requests used to fetch API data
import requests
import os
import sys
import urllib.parse

# Allow for silencing insecure warnings from requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Builtin JSON module for testing - might not need later
import json

# Needed for sleep and exporter start/end time metrics
import time

# argparse module used for providing command-line interface
import argparse

# Prometheus modules for HTTP server & metrics
from prometheus_client import start_http_server, Summary
from prometheus_client.core import GaugeMetricFamily, CounterMetricFamily, InfoMetricFamily, REGISTRY

import signal

# Compatible Ruckus API version
apiVersion = 'v11_1'

# Create SmartZoneCollector as a class - in Python3, classes inherit object as a base class
# Only need to specify for compatibility or in Python2

class SmartZoneCollector():

    # Initialize the class and specify required argument with no default value
    # When defining class methods, must explicitly list `self` as first argument
    def __init__(self, target, user, password, insecure):
        # Strip any trailing "/" characters from the provided url
        self._target = target.rstrip("/")
        # Take these arguments as provided, no changes needed
        self._user = user
        self._password = password
        self._insecure = insecure

        self._compatible = False
        self._headers = {'Content-Type': 'application/json;charset=UTF-8'}
        self._service_ticket = ''

        self._wlan_details = os.environ['WLAN_DETAILS'].split(',')

        # With the exception of uptime, all of these metrics are strings
        # Following the example of node_exporter, we'll set these string metrics with a default value of 1

    def get_session(self):
        # Disable insecure request warnings if SSL verification is disabled
        if self._insecure == False:
             requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        # Session object used to keep persistent cookies and connection pooling
        s = requests.Session()

        # Verify version compatibility
        r = s.get('{}/wsg/api/public/apiInfo'.format(self._target), verify=self._insecure)
        supported_versions = r.json().get('apiSupportVersions')
        self._compatible = any(apiVersion in x  for x in supported_versions)

        # Define URL arguments as a dictionary of strings 'payload'
        payload = {'username': self._user, 'password': self._password}

        # Call the payload using the json parameter
        r = s.post('{}/wsg/api/public/{}/serviceTicket'.format(self._target, apiVersion), json=payload, verify=self._insecure)

        # Raise bad requests
        r.raise_for_status()

        # Create a dictionary from the cookie name-value pair, then get the value based on the JSESSIONID key
        self._service_ticket = r.json().get('serviceTicket')


    def get_data(self, api_path):
        # Add the individual URL paths for the API call
        if 'query' in api_path:
            # For APs, use POST and API query to reduce number of requests and improve performance
            # To-do: set dynamic AP limit based on SmartZone inventory
            raw = {'page': 1, 'limit': 1000}
            r = requests.post('{}/wsg/api/public/{}/{}?serviceTicket={}'.format(self._target, apiVersion, api_path, self._service_ticket), json=raw, headers=self._headers, verify=self._insecure)
        else:
            r = requests.get('{}/wsg/api/public/{}/{}?serviceTicket={}'.format(self._target, apiVersion, api_path, self._service_ticket), headers=self._headers, verify=self._insecure)
        result = r.json()
        return result


    def collect(self):

        yield InfoMetricFamily('api_compatibility', 'Compatibility with exporter and controller', value={'compatible': str(self._compatible)})

        controller_metrics = {
            'model':
                GaugeMetricFamily('smartzone_controller_model',
                'SmartZone controller model',
                labels=["id", "model"]),
            'serialNumber':
                GaugeMetricFamily('smartzone_controller_serial_number',
                'SmartZone controller serial number',
                labels=["id", "serialNumber"]),
            'uptimeInSec':
                CounterMetricFamily('smartzone_controller_uptime_seconds',
                'Controller uptime in sections',
                labels=["id"]),
            'hostName':
                GaugeMetricFamily('smartzone_controller_hostname',
                'Controller hostname',
                labels=["id", "hostName"]),
            'version':
                GaugeMetricFamily('smartzone_controller_version',
                'Controller version',
                labels=["id", "version"]),
            'apVersion':
                GaugeMetricFamily('smartzone_controller_ap_firmware_version',
                'Firmware version on controller APs',
                labels=["id", "apVersion"])
                }

        zone_metrics = {
            'totalAPs':
                GaugeMetricFamily('smartzone_zone_total_aps',
                'Total number of APs in zone',
                labels=["zone_name","zone_id"]),
            'discoveryAPs':
                GaugeMetricFamily('smartzone_zone_discovery_aps',
                'Number of zone APs in discovery state',
                labels=["zone_name","zone_id"]),
            'connectedAPs':
                GaugeMetricFamily('smartzone_zone_connected_aps',
                'Number of connected zone APs',
                labels=["zone_name","zone_id"]),
            'disconnectedAPs':
                GaugeMetricFamily('smartzone_zone_disconnected_aps',
                'Number of disconnected zone APs',
                labels=["zone_name","zone_id"]),
            'rebootingAPs':
                GaugeMetricFamily('smartzone_zone_rebooting_aps',
                'Number of zone APs in rebooting state',
                labels=["zone_name","zone_id"]),
            'clients':
                GaugeMetricFamily('smartzone_zone_total_connected_clients',
                'Total number of connected clients in zone',
                labels=["zone_name","zone_id"])
                }

        ap_metrics = {
            'alerts':
                GaugeMetricFamily('smartzone_ap_alerts',
                'Number of AP alerts',
                labels=["zone","ap_group","mac","name","lat","long"]),
            'latency24G':
                GaugeMetricFamily('smartzone_ap_latency_24g_milliseconds',
                'AP latency on 2.4G channels in milliseconds',
                labels=["zone","ap_group","mac","name","lat","long"]),
            'latency50G':
                GaugeMetricFamily('smartzone_ap_latency_5g_milliseconds',
                'AP latency on 5G channels in milliseconds',
                labels=["zone","ap_group","mac","name","lat","long"]),
            'latency6G':
                GaugeMetricFamily('smartzone_ap_latency_6g_milliseconds',
                'AP latency on 6G channels in milliseconds',
                labels=["zone","ap_group","mac","name","lat","long"]),
            'numClients24G':
                GaugeMetricFamily('smartzone_ap_connected_clients_24g',
                'Number of clients connected to 2.4G channels on this AP',
                labels=["zone","ap_group","mac","name","lat","long"]),
            'numClients5G':
                GaugeMetricFamily('smartzone_ap_connected_clients_5g',
                'Number of clients connected to 5G channels on this AP',
                labels=["zone","ap_group","mac","name","lat","long"]),
            'numClients6G':
                GaugeMetricFamily('smartzone_ap_connected_clients_6g',
                'Number of clients connected to 6G channels on this AP',
                labels=["zone","ap_group","mac","name","lat","long"]),
            'status':
                GaugeMetricFamily('smartzone_ap_status',
                'AP status',
                labels=["zone","ap_group","mac","name","status","lat","long"]),
            'model':
                GaugeMetricFamily('smartzone_ap_model',
                'AP model',
                labels=["zone","ap_group","mac","name","model","lat","long"]),
        }

        wlan_metrics = {
            'alerts':
                GaugeMetricFamily('smartzone_wlan_alerts',
                'Number of WLAN alerts',
                labels=["zone","name","ssid"]),                
            'clients':
                GaugeMetricFamily('smartzone_wlan_connected_clients',
                'Number of clients connected to this SSID',
                labels=["zone","name","ssid"]),
        }

        details_metrics = {
            'passphrase':
                GaugeMetricFamily('smartzone_wlan_details_passphrase',
                'WLAN details Passphrase',
                labels=["zone","name","ssid","passphrase","qrcode"]),
            'schedule':
                GaugeMetricFamily('smartzone_wlan_details_schedule',
                'WLAN Details Schedule',
                labels=["zone","name","ssid","schedule_name","sun","mon","tue","wed","thu","fri","sat"]),
        }

        self.get_session()

        # Get SmartZone controller metrics
        for c in self.get_data('controller')['list']:
            id = c['id']
            for s in list(controller_metrics.keys()):
                if s == 'uptimeInSec':
                     controller_metrics[s].add_metric([id], c.get(s))
                # Export a dummy value for string-only metrics
                else:
                     extra = c[s]
                     controller_metrics[s].add_metric([id, extra], 1)

        for m in controller_metrics.values():
            yield m

        # Get SmartZone inventory per zone
        # For each zone captured from the query:
        # - Grab the zone name and zone ID for labeling purposes
        # - Loop through the metrics
        # - For each status, get the value for the status in each zone and add to the metric
        for zone in sorted(self.get_data('system/inventory')['list'], key=lambda d: d['zoneName']):
            zone_name = zone['zoneName']
            zone_id = zone['zoneId']
            for s in list(zone_metrics.keys()):
                zone_metrics[s].add_metric([zone_name, zone_id], zone.get(s))

        for m in zone_metrics.values():
            yield m

        # Get SmartZone AP metrics
        # Generate the metrics based on the values
        for ap in sorted(self.get_data('query/ap')['list'], key=lambda d: d['deviceName']):
            try:
                lat = ap.get('deviceGps').split(',')[0]
                long = ap.get('deviceGps').split(',')[1]
            except:
                lat = 'none'
                long = 'none'
            for s in list(ap_metrics.keys()):
                # 'Status' is a string value only, so we can't export the default value
                if s == 'status':
                    state_name = ['Online','Offline','Flagged']
                    # By default set value to 0 and increase to 1 to reflect current state
                    # Similar to how node_exporter handles systemd states
                    for n in state_name:
                        value = 0
                        if ap.get(s) == str(n):
                            value = 1
                        # Wrap the zone and group names in str() to avoid issues with None values at export time
                        ap_metrics[s].add_metric([str(ap['zoneName']), str(ap['apGroupName']), ap['apMac'], ap['deviceName'], n, lat, long], value)
                elif s == 'model':
                    ap_metrics[s].add_metric([str(ap['zoneName']), str(ap['apGroupName']), ap['apMac'], ap['deviceName'], ap['model'], lat, long], 1)
                else:
                    if ap.get(s) is not None:
                        ap_metrics[s].add_metric([str(ap['zoneName']), str(ap['apGroupName']), ap['apMac'], ap['deviceName'], lat, long], ap.get(s))
                    # Return 0 for metrics with values of None
                    else:
                        ap_metrics[s].add_metric([str(ap['zoneName']), str(ap['apGroupName']), ap['apMac'], ap['deviceName'], lat, long], 0)

        for m in ap_metrics.values():
            yield m

        for wlan in sorted(self.get_data('query/wlan')['list'], key=lambda d: d['name']):
            for s in list(wlan_metrics.keys()):
                if wlan.get(s) in [True, False]:
                    wlan_metrics[s].add_metric([str(wlan['zoneName']), str(wlan['name']), wlan['ssid']], +wlan.get(s))
                elif wlan.get(s) is not None:
                    wlan_metrics[s].add_metric([str(wlan['zoneName']), str(wlan['name']), wlan['ssid']], wlan.get(s))
                # Return 0 for metrics with values of None
                else:
                    wlan_metrics[s].add_metric([str(wlan['zoneName']), str(wlan['name']), wlan['ssid']], 0)
            if wlan['ssid'] in self._wlan_details:
                wlan_data = self.get_data('rkszones/{}/wlans/{}'.format(wlan['zoneId'], wlan['wlanId']))
                if wlan_data['encryption']['method'] == 'WPA2':
                    details_metrics['passphrase'].add_metric([str(wlan['zoneName']), str(wlan['name']), wlan['ssid'], wlan_data['encryption']['passphrase'],
                        'https://api.qrserver.com/v1/create-qr-code/?size=350x350&data=WIFI:T:WPA;S:{};P:{};;'.format(wlan['ssid'], urllib.parse.quote_plus(wlan_data['encryption']['passphrase']))
                      ], 1)
                else:
                    details_metrics['passphrase'].add_metric(str(wlan['zoneName']), str(wlan['name']), wlan['ssid'], "-", 0)
                if wlan_data['schedule']['type'] in ['AlwaysOff', 'AlwaysOn']:
                    details_metrics['schedule'].add_metric([str(wlan['zoneName']), str(wlan['name']), wlan['ssid'], str(wlan_data['schedule']['type']), "-", "-", "-", "-", "-", "-", "-" ], 0)
                elif wlan_data['schedule']['id'] != 'None':
                    schedule = self.get_data('rkszones/{}/wlanSchedulers/{}'.format(wlan['zoneId'], wlan_data['schedule']['id']))
                    details_metrics['schedule'].add_metric([str(wlan['zoneName']), str(wlan['name']), wlan['ssid'], schedule['name'],
                        ','.join(schedule["sun"]) if len(schedule["sun"]) > 0 else "-",
                        ','.join(schedule["mon"]) if len(schedule["mon"]) > 0 else "-",
                        ','.join(schedule["tue"]) if len(schedule["tue"]) > 0 else "-",
                        ','.join(schedule["wed"]) if len(schedule["wed"]) > 0 else "-",
                        ','.join(schedule["thu"]) if len(schedule["thu"]) > 0 else "-",
                        ','.join(schedule["fri"]) if len(schedule["fri"]) > 0 else "-",
                        ','.join(schedule["sat"]) if len(schedule["sat"]) > 0 else "-"
                        ], 0)

        for m in wlan_metrics.values():
            yield m

#        for zone in sorted(self.get_data('rkszones')['list'], key=lambda d: d['name']):
#            zone_name = zone['name']
#            zone_id = zone['id']
#            for wlan in sorted(self.get_data('rkszones/{}/wlans'.format(zone_id))['list'], key=lambda d: d['name']):
#                if wlan['ssid'] in self._wlan_details:
#                    wlan_id = wlan['id']
#                    wlan_data = self.get_data('rkszones/{}/wlans/{}'.format(zone_id, wlan_id))
#                    if wlan_data['encryption']['method'] == 'WPA2':
#                        details_metrics['passphrase'].add_metric([zone_name, str(wlan['name']), wlan['ssid'], wlan_data['encryption']['passphrase']], 1)
#                        details_metrics['qrcode'].add_metric([zone_name, str(wlan['name']), wlan['ssid'],
#                            'https://api.qrserver.com/v1/create-qr-code/?size=350x350&data=WIFI:T:WPA;S:{};P:{};;'.format(wlan['ssid'], urllib.parse.quote_plus(wlan_data['encryption']['passphrase']))
#                            ], 1)
#                    if wlan_data['schedule']['type'] in ['AlwaysOff', 'AlwaysOn']:
#                        details_metrics['schedule'].add_metric([zone_name, str(wlan['name']), wlan['ssid'], str(wlan_data['schedule']['type']), "-", "-", "-", "-", "-", "-", "-" ], 0)
#                    elif wlan_data['schedule']['id'] != 'None':
#                        schedule = self.get_data('rkszones/{}/wlanSchedulers/{}'.format(zone_id, wlan_data['schedule']['id']))
#                        details_metrics['schedule'].add_metric([zone_name, str(wlan['name']), wlan['ssid'], schedule['name'],
#                            ','.join(schedule["sun"]) if len(schedule["sun"]) > 0 else "-",
#                            ','.join(schedule["mon"]) if len(schedule["mon"]) > 0 else "-",
#                            ','.join(schedule["tue"]) if len(schedule["tue"]) > 0 else "-",
#                            ','.join(schedule["wed"]) if len(schedule["wed"]) > 0 else "-",
#                            ','.join(schedule["thu"]) if len(schedule["thu"]) > 0 else "-",
#                            ','.join(schedule["fri"]) if len(schedule["fri"]) > 0 else "-",
#                            ','.join(schedule["sat"]) if len(schedule["sat"]) > 0 else "-" 
#                            ], 0)

        for m in details_metrics.values():
            yield m



# Function to parse command line arguments and pass them to the collector
def parse_args():
    parser = argparse.ArgumentParser(description='Ruckus SmartZone exporter for Prometheus')

    # Use add_argument() method to specify options
    # By default argparse will treat any arguments with flags (- or --) as optional
    # Rather than make these required (considered bad form), we can create another group for required options
    required_named = parser.add_argument_group('required named arguments')
    required_named.add_argument('-t', '--target', help='Target URL and port to access SmartZone, e.g. https://smartzone.example.com:8443', required=True)

    # Add store_false action to store true/false values, and set a default of True
    parser.add_argument('--insecure', action='store_false', help='Allow insecure SSL connections to Smartzone')

    # Specify integer type for the listening port
    parser.add_argument('--port', type=int, default=9345, help='Port on which to expose metrics and web interface (default=9345)')

    # Now that we've added the arguments, parse them and return the values as output
    return parser.parse_args()

def terminate(signal,frame):
    print("Exiting...")
    sys.exit(0)

def main():
    signal.signal(signal.SIGTERM, terminate)

    args = parse_args()
    port = int(args.port)
    user = os.environ['API_USER']
    password = os.environ['API_PASSWORD']
    REGISTRY.register(SmartZoneCollector(args.target, user, password, args.insecure))
    # Start HTTP server on specified port
    start_http_server(port)
    if args.insecure == False:
            print('WARNING: Connection to {} may not be secure.'.format(args.target))
    print("Polling {}. Listening on ::{}".format(args.target, port))
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
