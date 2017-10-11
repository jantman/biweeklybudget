#!/bin/bash

# to incorporate: https://github.com/Jaymon/wishlist/pull/8
# licensed under GPL v2
pip install --upgrade --target . --no-deps git+https://github.com/jantman/wishlist.git@c362e59b9388f65bfa39a8c807af04f6041265b3#egg=wishlist
curl -o wishlist/LICENSE.txt https://raw.githubusercontent.com/jantman/wishlist/c362e59b9388f65bfa39a8c807af04f6041265b3/LICENSE.txt
curl -o wishlist/setup.py https://raw.githubusercontent.com/jantman/wishlist/c362e59b9388f65bfa39a8c807af04f6041265b3/setup.py
