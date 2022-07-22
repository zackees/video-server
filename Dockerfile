# FROM ubuntu:22.04
FROM python:3.10-slim-bullseye

# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

RUN apt-get install -y npm nodejs

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
