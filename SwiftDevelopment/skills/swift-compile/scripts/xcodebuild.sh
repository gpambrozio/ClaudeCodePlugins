#!/usr/bin/env bash

set -e
set -u
set -o pipefail

"$(dirname "$0")/xcsift-install.sh"

xcodebuild -skipMacroValidation -skipPackagePluginValidation "$@" 2>&1 | xcsift
exit ${PIPESTATUS[0]}
