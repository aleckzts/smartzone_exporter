# using ubuntu LTS version
FROM ubuntu:20.04 AS builder-image

# avoid stuck build due to user prompt
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y python3.9 python3-wheel pipenv && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pipenv install

CMD ["python3 /smartzone/smartzone_exporter.py"]
