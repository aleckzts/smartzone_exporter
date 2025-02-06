# using ubuntu LTS version
FROM ubuntu:20.04 AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /smartzone

RUN apt-get update && apt-get install -y python3.9 python3-pip && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip3 install -r requirements.txt

EXPOSE 9345

CMD ["/usr/bin/python3 /smartzone/smartzone_exporter.py -u $API_USER -p $API_PASSWORD -t $VSZ_TARGET $EXTRA_PARAM"]
