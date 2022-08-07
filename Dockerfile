# FROM ubuntu:22.04
FROM --platform=linux/amd64 python:3.10.5-bullseye

# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --force-yes --no-install-recommends \
    apt-transport-https \
    ca-certificates \
    sudo \
    mktorrent \
    curl

WORKDIR /app

# Install all the dependencies as it's own layer.
COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install magic-wormhole

# Add requirements file and install.
COPY . .

# RUN python -m pip install --no-cache-dir -e .
# RUN ./install.sh

RUN python -m pip install -e .

# Expose the port and then launch the app.
EXPOSE 80


# Note reload allows restart by file touch.
#CMD ["uvicorn", "--host", "0.0.0.0", "--reload", "--reload-exclude", "*", "--reload-include", "reload.file", "--workers", "1", "--ws", "websockets", "--forwarded-allow-ips", "*", "--port", "80", "--debug", "true", "webtorrent_movie_server.app:app"]
#CMD ["webtorrent-hybrid", "seed", "--keep-seeding", "make_venv.py", "--announce", "wss://webtorrent-tracker.onrender.com", "--port", "8000"]
# CMD ["/bin/bash", "run.sh"]
CMD ["uvicorn", "--host", "0.0.0.0", "--reload", "--reload-dir", "restart", "--workers", "1", "--forwarded-allow-ips=*", "--port", "80", "webtorrent_movie_server.app:app"]
