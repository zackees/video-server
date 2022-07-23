# uvicorn --host 0.0.0.0 --reload --reload-exclude * --reload-include reload.file --workers 1 --ws websockets --forwarded-allow-ips * --port 80 --debug true webtorrent_movie_server.app:app
uvicorn --host 0.0.0.0:80 --reload --reload-dir restart --workers 1 --ws websockets --forwarded-allow-ips=* --port 80 webtorrent_movie_server.app:app
