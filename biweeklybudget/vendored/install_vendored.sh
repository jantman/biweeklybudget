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

# to incorporate https://github.com/jseutter/ofxparse/pull/127 which was merged but not released
# licensed under the MIT License
pip install --upgrade --target . --no-deps git+https://github.com/jseutter/ofxparse.git@19c04b40e2c7c3cb2943344f6108bcaf3d968725#egg=ofxparse
curl -o ofxparse/LICENSE https://raw.githubusercontent.com/jseutter/ofxparse/19c04b40e2c7c3cb2943344f6108bcaf3d968725/LICENSE
curl -o ofxparse/setup.py.src https://raw.githubusercontent.com/jseutter/ofxparse/19c04b40e2c7c3cb2943344f6108bcaf3d968725/setup.py

sed -i 's/from ofxparse import/from biweeklybudget.vendored.ofxparse import/g' ofxclient/*.py
