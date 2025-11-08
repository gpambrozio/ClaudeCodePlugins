#!/usr/bin/env bash

set -e
set -u
set -o pipefail

"$(dirname "$0")/xcsift-install.sh"

swift "$@" 2>&1 | xcsift --warnings
exit ${PIPESTATUS[0]}
