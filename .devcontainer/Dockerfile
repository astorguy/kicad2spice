FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

WORKDIR /app

COPY bookworm-backports.list /etc/apt/sources.list.d/

# install ngspice
RUN apt-get update && \
    sudo apt-get -y install ngspice && \
    sudo apt-get -t bookworm-backports -y install kicad && \
    rm -rf /var/lib/apt/lists/*

# intstall my Python modules
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN rm ./requirements.txt
