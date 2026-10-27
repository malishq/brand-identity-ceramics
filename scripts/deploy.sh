#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
REMOTE=$(git remote get-url origin)
rm -rf site && mkdir site
cp -R brandbook/. site/
touch site/.nojekyll
rm -rf .deploy && cp -R site .deploy
cd .deploy && git init -q -b gh-pages && git add -A && git commit -qm "Deploy $(date +%F)" && git push -f "$REMOTE" gh-pages:gh-pages
cd .. && rm -rf .deploy
echo "gh-pages pushed: https://malishq.github.io/brand-identity-ceramics/"
