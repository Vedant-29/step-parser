#!/bin/bash

# Start Xvfb (X Virtual Framebuffer) for headless rendering
echo "Starting Xvfb virtual display..."
Xvfb :99 -screen 0 ${XVFB_WHD:-1920x1080x24} -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait a moment for Xvfb to start
sleep 2

# Activate conda environment
source /opt/conda/etc/profile.d/conda.sh
conda activate membership_transfer

# Function to cleanup on exit
cleanup() {
    echo "Stopping Xvfb..."
    kill $XVFB_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGTERM SIGINT EXIT

echo "Starting Flask application..."
python app.py