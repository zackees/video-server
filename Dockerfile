# FROM ubuntu:22.04
FROM --platform=linux/amd64 python:3.10.5-bullseye
# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
# All the useful binary commands.
RUN apt-get update && apt-get install -y --force-yes --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    sudo \
    mktorrent \
    curl npm
WORKDIR /app
RUN pip install --upgrade pip
RUN pip install magic-wormhole
RUN npm install http-server -g
# for sending files to other devices
COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
COPY . .
RUN python -m pip install -e .
# Expose the port and then launch the app.
EXPOSE 80
EXPOSE 8000
CMD ["/bin/sh", "./entry_point.sh"]
