# FROM ubuntu:22.04
FROM --platform=linux/amd64 python:3.10.5-bullseye

# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --force-yes --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common \
    git-all \
    pkg-config \
    libncurses5-dev \
    libssl-dev \
    libnss3-dev \
    libexpat-dev \
    npm \
    nodejs 
#&& rm -rf /var/lib/apt/lists/*;


RUN apt-get install -y npm nodejs


# From the webtorrent-hybrid dockerfile.

RUN apt-get install -y \
    libgtk2.0-dev \
    libgconf-2-4 \
    libasound2 \
    libxtst6 \
    libxss1 \
    libnss3 \
    xvfb \
    git


#RUN apt-get full-upgrade -y && \
#    apt-get install -y libgtk2.0-dev libgconf-2-4 libasound2 libxtst6 libxss1 libnss3 xvfb git -y && \
#    apt-get autoremove --purge -y && \
#    rm -rf /var/lib/apt/lists/* && \
#    npm i -g node-pre-gyp

WORKDIR /app

# Install all the dependencies as it's own layer.
COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir  -r requirements.txt

# Add requirements file and install.
COPY . .

# RUN python -m pip install --no-cache-dir -e .
RUN ./install.sh

# Expose the port and then launch the app.
EXPOSE 80
EXPOSE 8000

# Note reload allows restart by file touch.
CMD ["uvicorn", "--host", "0.0.0.0", "--reload", "--port", "80", "webtorrent_movie_server.app:app"]
