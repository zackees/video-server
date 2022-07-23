set -e
cd $( dirname ${BASH_SOURCE[0]})
source ./activate.sh
python -m webbrowser -t "http://127.0.0.1:80"
uvicorn webtorrent_movie_server.app:app --no-use-colors --reload --port 80 --host 0.0.0.0
CMD ["uvicorn", "--host", "0.0.0.0", "--reload", "--reload-exclude", "*", "--reload-include", "reload.file", "--workers", "1", "--ws", "websockets", "--forwarded-allow-ips", "*", "--port", "80", "--debug", "true", "webtorrent_movie_server.app:app"]
