set -e
cd $( dirname ${BASH_SOURCE[0]})
source ./activate.sh
python webtorrent_movie_server/app.py
