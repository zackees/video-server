set -e
cd $( dirname ${BASH_SOURCE[0]})
source ./activate.sh
python video_server/app.py
