uvicorn --host 0.0.0.0 --port 80 --reload --reload-dir restart --workers 100 --forwarded-allow-ips=* video_server.app:app
