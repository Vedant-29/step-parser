#!/bin/bash
source /opt/conda/etc/profile.d/conda.sh
conda activate membership_transfer

# Debug X11 setup
echo "=== X11 Debug Information ==="
echo "DISPLAY: $DISPLAY"
echo "XAUTHORITY: $XAUTHORITY"
echo "X11 socket exists: $(ls -la /tmp/.X11-unix/ 2>/dev/null || echo 'NOT FOUND')"
echo "Xauthority file exists: $(ls -la $XAUTHORITY 2>/dev/null || echo 'NOT FOUND')"

# Test if we can connect to X11 display using a simpler method
echo "Testing X11 connection with xdpyinfo..."
if command -v xdpyinfo >/dev/null 2>&1; then
    if xdpyinfo -display $DISPLAY >/dev/null 2>&1; then
        echo "✓ X11 display $DISPLAY is accessible"
    else
        echo "✗ X11 display $DISPLAY is NOT accessible"
        echo "Trying without XAUTHORITY..."
        unset XAUTHORITY
        if xdpyinfo -display $DISPLAY >/dev/null 2>&1; then
            echo "✓ X11 display works without XAUTHORITY"
        else
            echo "✗ X11 display still not working"
        fi
    fi
else
    echo "xdpyinfo not available, trying xset..."
    if xset q >/dev/null 2>&1; then
        echo "✓ X11 display $DISPLAY is accessible via xset"
    else
        echo "✗ X11 display $DISPLAY is NOT accessible via xset"
    fi
fi

echo "=== Starting Flask Application ==="
python app.py