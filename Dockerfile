# Use linux/amd64, or else the build will fail to on mac-m1
FROM --platform=linux/amd64 node:slim

RUN apt-get update && \
	apt-get full-upgrade -y && \
	apt-get install -y libgtk2.0-0 libgconf-2-4 libasound2 libxtst6 libxss1 libnss3 xvfb git -y && \
	apt-get autoremove --purge -y && \
	rm -rf /var/lib/apt/lists/* && \
	npm i -g node-pre-gyp


RUN npm install -g https://github.com/zackees/webtorrent-hybrid
RUN npm install -g http-server

#RUN npm i -g webtorrent-hybrid && \
#	mkdir -p /webtorrent

EXPOSE 80
WORKDIR /webtorrent

# COPY . .
# RUN npm install -g .
# ENTRYPOINT ["/usr/local/bin/webtorrent-hybrid"]
# CMD ["/bin/sh", "-c", "bash", "-it"]

CMD ["http-server", "-p", "80"]

# docker buildx build --platform linux/amd64 --push -t wtapp .
# docker run -it wtapp
# webtorrent-hybrid seed foo.txt --announce wss://webtorrent-tracker.onrender.com --port 80 --keep-seeding