#!/bin/bash

# to incorporate: https://github.com/Jaymon/wishlist/pull/8
# licensed under GPL v2
pip install --upgrade --target . --no-deps git+https://github.com/jantman/wishlist.git@c362e59b9388f65bfa39a8c807af04f6041265b3#egg=wishlist
curl -o wishlist/LICENSE.txt https://raw.githubusercontent.com/jantman/wishlist/c362e59b9388f65bfa39a8c807af04f6041265b3/LICENSE.txt
curl -o wishlist/setup.py.src https://raw.githubusercontent.com/jantman/wishlist/c362e59b9388f65bfa39a8c807af04f6041265b3/setup.py

# to incorporate: https://github.com/captin411/ofxclient/pull/47
# licensed under the MIT License
pip install --upgrade --target . --no-deps git+https://github.com/jantman/ofxclient.git@afa8d2175483bf4f50632179f434021782f49d9c#egg=ofxclient
curl -o ofxclient/LICENSE https://raw.githubusercontent.com/jantman/ofxclient/afa8d2175483bf4f50632179f434021782f49d9c/LICENSE
curl -o ofxclient/setup.py.src https://github.com/jantman/ofxclient/raw/afa8d2175483bf4f50632179f434021782f49d9c/setup.py

sed -i -r 's/^([[:space:]]*)from ofxclient/\1from biweeklybudget.vendored.ofxclient/g' ofxclient/*.py
