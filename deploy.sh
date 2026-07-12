#!/bin/bash
# Deploy the Sponsor Logos app to a connected Tildagon badge via mpremote.
#
# Usage: ./deploy.sh [device]
#   device  — serial port (default: auto-detect)

set -e

DEVICE="${1:-auto}"
APP_NAME="emfcamp_tildagon_sponsor_logos"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$DEVICE" = "auto" ]; then
    CONNECT="mpremote"
else
    CONNECT="mpremote connect $DEVICE"
fi

echo "Creating app directory on badge..."
$CONNECT mkdir /apps/$APP_NAME 2>/dev/null || true
$CONNECT mkdir /apps/$APP_NAME/logos 2>/dev/null || true

echo "Copying app files..."
$CONNECT \
    cp "$SCRIPT_DIR/app.py" :/apps/$APP_NAME/app.py \
    + cp "$SCRIPT_DIR/metadata.json" :/apps/$APP_NAME/metadata.json \
    + cp "$SCRIPT_DIR/tildagon.toml" :/apps/$APP_NAME/tildagon.toml

echo "Copying logos..."
CMD="$CONNECT"
FIRST=true
for f in "$SCRIPT_DIR"/logos/*.jpg; do
    BASENAME=$(basename "$f")
    if [ "$FIRST" = true ]; then
        CMD="$CMD cp $f :/apps/$APP_NAME/logos/$BASENAME"
        FIRST=false
    else
        CMD="$CMD + cp $f :/apps/$APP_NAME/logos/$BASENAME"
    fi
done
eval $CMD

echo "Resetting badge..."
$CONNECT reset

echo "Done! The app should appear in the launcher."
