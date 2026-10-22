#!/bin/bash
# Build the participant download: dist/screenplay-converter-<version>.zip
set -euo pipefail
cd "$(dirname "$0")/.."
version=$(python3 -c "import json;print(json.load(open('plugin/.claude-plugin/plugin.json'))['version'])")
name="screenplay-converter"
stage="dist/$name"
mkdir -p dist
rm -rf "$stage" "dist/$name-$version.zip"
mkdir -p "$stage"
cp -R .claude-plugin plugin install.py README.md README.fi.md "$stage/"
find "$stage" \( -name '__pycache__' -o -name '.DS_Store' -o -name '*.pyc' \) -prune -exec rm -rf {} +
(cd dist && zip -qr "$name-$version.zip" "$name")
rm -rf "$stage"
echo "dist/$name-$version.zip"
unzip -l "dist/$name-$version.zip" | tail -1
