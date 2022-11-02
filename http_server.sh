# Get $DATA_ROOT from the environment
# If $DATA_ROOT is unset
if [ -z "$DATA_ROOT" ]; then
    # Error, we need to set $DATA_ROOT
    echo "ERROR: DATA_ROOT is unset"
    exit 1
fi
http-server $DATA_ROOT/www -p 7777 --cors=*
