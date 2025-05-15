# SmartZone Exporter

Forked from [ddericco/smartzone_exporter](https://github.com/ddericco/smartzone_exporter)

Ruckus SmartZone exporter for https://prometheus.io, written in Python.

This exporter is adapted in part from examples by [Robust Perception](https://www.robustperception.io/writing-a-jenkins-exporter-in-python/) and [Loovoo](https://github.com/lovoo/jenkins_exporter), utilizing the [Ruckus SmartZone API](https://docs.ruckuswireless.com/smartzone/6.1.1/vszh-public-api-reference-guide-611.html) to query for metrics.

## Background
The goal of this exporter is twofold: provide a faster and more reliable alternative to SNMP for querying metrics from a Ruckus SmartZone controller, while also providing an opportunity to brush up on my (admittedly quite rusty) Python skills. Most of the code will be heavily commented with notes that would be obvious to more experienced developers; perhaps it will be useful for other contributors or developers. There will certainly be additional efficiencies that can be gained, more 'Pythonic' ways of doing certain tasks, or other changes that make this exporter better; contributions are always welcome!

## Features
The following metrics are currently supported:
* Controller summary (uptime, model, serial, hostname, version, AP firmware version)
* System inventory (total APs, discovery APs, connected APs, disconnected APs, rebooting APs, clients)
* AP statistics (status, alerts, latency, connected clients, GPS)

Additional metrics may be added over time.

## Usage
Create an .env file with the target URL, username and password. You can add a list with SSIDs that will be included with more details (passphrase and schedule)

```
VSZ_TARGET="https://smartzone.example.com:8443/"
API_USER="myusername"
API_PASSWORD="mypass"
WLAN_DETAILS=SSID1,SSID2
```

Build the image and run

```
docker compose build
docker compose up -d
```

## Requirements
This exporter has been tested on the following versions:

| Model | Version     |
|-------|-------------|
| vSZ-H | 6.1.1.0.959 |

## Installation
```
git clone https://github.com/aleckzts/smartzone_exporter.git
cd smartzone_exporter
docker compose build
docker compose up -d
```


## Prometheus
```
  - job_name: ruckus_wifi
    scrape_interval: 30s
    scrape_timeout: 25s
    static_configs:
      - targets: ["localhost:9345"]
    metrics_path: /metrics
```
