cd $( dirname ${BASH_SOURCE[0]})
python ./make_venv.py
. ./activate.sh
python -m pip install pip --upgrade
python -m pip install . -e
cp webtorrent_movie_server/pre-commit .git/hooks/pre-commit | true
