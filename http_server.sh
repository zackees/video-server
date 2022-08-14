# if $DATA_ROOT unset then error
if [ -z "$DATA_ROOT" ]; then
    # Error
    echo "DATA_ROOT is unset"
    exit 1
fi

http-server $DATA_ROOT/www -p 80 --cors=* --proxy http://localhost:8000
