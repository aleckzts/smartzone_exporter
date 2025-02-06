FROM ubuntu:20.04

WORKDIR /smartzone

RUN apt-get update && apt-get install -y python3 pipenv

COPY . .

RUN pipenv install

CMD ["python3 /smartzone/smartzone_exporter.py"]
