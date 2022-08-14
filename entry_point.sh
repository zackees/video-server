
# If $DATA_ROOT is unset
if [ -z "$DATA_ROOT" ]; then
    DATA_ROOT="/app/var/data"
fi
mkdir -p $DATA_ROOT
# First launch the uvicorn server
uvicorn --host localhost --port 8000 --reload --reload-dir restart --workers 100 --forwarded-allow-ips=* webtorrent_movie_server.app:app &
echo DATA_ROOT is $DATA_ROOT
# The http-server has the proper settings to allow efficient video streaming, we need to use both
# servers to enable streaming of video.
pm2 start http-server -- $DATA_ROOT/www -p 80 --cors='*' --proxy http://localhost:8000
pm2 logs
