#!/bin/sh

/bin/python3 /smartzone/smartzone_exporter.py -u ${API_USER} -p ${API_PASSWORD} -t ${VSZ_TARGET} ${EXTRA_PARAM}
