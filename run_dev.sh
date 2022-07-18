set -e
cd $( dirname ${BASH_SOURCE[0]})
python -m webbrowser -t "http://127.0.0.1:80"
uvicorn webtorrent_movie_server.app:app --no-use-colors --reload --port 80 --host 0.0.0.0
