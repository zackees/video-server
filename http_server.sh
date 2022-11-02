# Get $DATA_ROOT from the environment
# If $DATA_ROOT is unset
if [ -z "$DATA_ROOT" ]; then
    # Error, we need to set $DATA_ROOT
    echo "ERROR: DATA_ROOT is unset"
    exit 1
fi
# if FILE_PORT is unset
if [ -z "$FILE_PORT" ]; then
    echo "ERROR: FILE_PORT is unset"
    exit 1
fi
echo http-server $DATA_ROOT/www -p $FILE_PORT --cors=*
http-server $DATA_ROOT/www -p $FILE_PORT --cors=*
