
# If $DATA_ROOT is unset
if [ -z "$DATA_ROOT" ]; then
    DATA_ROOT="/app/var/data"
fi
export DATA_ROOT
set -e
mkdir -p $DATA_ROOT
# First launch the uvicorn server
pm2 start ./unicorn.sh
echo DATA_ROOT is $DATA_ROOT
# The http-server has the proper settings to allow efficient video streaming, we need to use both
# servers to enable streaming of video.
pm2 start ./http_server.sh
pm2 logs
