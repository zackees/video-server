# FROM ubuntu:22.04
FROM python:3.10-slim-bullseye

# Might be necessary.
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

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

CMD ["uvicorn", "--host", "0.0.0.0", "--port", "80", "webtorrent_movie_server.app:app"]
