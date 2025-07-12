#!/bin/bash
source /opt/conda/etc/profile.d/conda.sh
conda activate membership_transfer

# Wait for X11 display to be available
echo "Waiting for X11 display $DISPLAY to be available..."
until xset q &>/dev/null; do
    echo "Display $DISPLAY not ready, waiting..."
    sleep 1
done
echo "Display $DISPLAY is ready!"

# Test X11 connection
echo "Testing X11 connection..."
xset q

# Start the application
echo "Starting Flask application..."
python app.py