# get default DATA_DIR
DATA_ROOT=${DATA_DIR:-/app/var/data}
export DATA_ROOT=$DATA_ROOT
mkdir -p $DATA_ROOT
uvicorn --host localhost --port 8000 --reload --reload-dir restart --workers 100 --forwarded-allow-ips=* webtorrent_movie_server.app:app &
echo DATA_ROOT is $DATA_ROOT
http-server $DATA_ROOT/www -p 80 --cors='*' --proxy http://localhost:8000
