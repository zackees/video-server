uvicorn --host 0.0.0.0 --port 80 --reload --reload-dir restart --workers 100 --forwarded-allow-ips=* webtorrent_movie_server.app:app
