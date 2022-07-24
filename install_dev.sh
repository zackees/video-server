cd $( dirname ${BASH_SOURCE[0]})
python make_venv.py
. activate.sh
python -m pip install -r requirements.txt
python -m pip install -r requirements.testing.txt
npm install -g https://github.com/zackees/webtorrent-hybrid
npm install -g https://github.com/zackees/bittorrent-tracker
