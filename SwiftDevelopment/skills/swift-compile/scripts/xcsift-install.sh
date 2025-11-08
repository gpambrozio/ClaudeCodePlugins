#!/usr/bin/env bash

set -e
set -u
set -o pipefail

# Check if xcsift is already installed
if hash xcsift 2>/dev/null; then
  if xcsift --version >/dev/null 2>&1; then
    # xcsift is installed and working, attempt to upgrade to latest
    brew upgrade xcsift >/dev/null 2>&1 || brew upgrade ldomaradzki/xcsift/xcsift >/dev/null 2>&1 || true
    exit 0
  else
    echo "Error: xcsift command exists but is not working properly. Try reinstalling: brew uninstall xcsift && brew install ldomaradzki/xcsift/xcsift" >&2
    exit 1
  fi
fi

# Check if Homebrew is installed
if ! hash brew 2>/dev/null; then
  echo "Error: Homebrew is not installed. Install it first: /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\" or install xcsift manually from https://github.com/ldomaradzki/xcsift" >&2
  exit 1
fi

# Start installation
echo "Installing xcsift... This might take a while."

# Try to tap the repository
if ! brew tap ldomaradzki/xcsift 2>/dev/null; then
  echo "Error: Failed to tap ldomaradzki/xcsift repository. This could be due to network issues, GitHub being unreachable, or the repository being moved. Try: brew update, check your internet connection, or install manually from https://github.com/ldomaradzki/xcsift" >&2
  exit 1
fi

# Try to install xcsift
if ! brew install xcsift 2>/dev/null; then
  if brew list xcsift >/dev/null 2>&1; then
    echo "Error: xcsift appears to be installed but the command is not available. Try: exec \$SHELL to reload shell, brew reinstall xcsift, or brew link xcsift" >&2
  else
    echo "Error: Failed to install xcsift. Possible causes: missing dependencies, insufficient disk space, or permission issues. Try: brew update && brew upgrade, sudo chown -R \$(whoami) \$(brew --prefix)/*, or brew install xcsift --verbose for details. Manual install: https://github.com/ldomaradzki/xcsift" >&2
  fi
  exit 1
fi

# Verify installation succeeded
if ! hash xcsift 2>/dev/null; then
  echo "Error: xcsift was installed but is not in PATH. Try: exec \$SHELL to reload shell, eval \"\$(brew shellenv)\" to add Homebrew to PATH, or check installation with brew list xcsift" >&2
  exit 1
fi

# Final verification
if ! xcsift --version >/dev/null 2>&1; then
  echo "Error: xcsift installed but is not functioning properly. Try reinstalling: brew reinstall xcsift" >&2
  exit 1
fi

echo "xcsift installed successfully"
