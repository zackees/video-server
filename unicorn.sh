uvicorn --host localhost --port 8000 --reload --reload-dir restart --workers 100 --forwarded-allow-ips=* webtorrent_movie_server.app:app
