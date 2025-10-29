#!/usr/bin/env bash

set -e
set -u
set -o pipefail

if ! hash xcsift 2>/dev/null; then
  echo "Installing xcsift... This might take a while."
  brew tap ldomaradzki/xcsift > /dev/null
  brew install xcsift > /dev/null
fi
