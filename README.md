# CAD Runner with Browser-Based VNC Desktop

This project lets you run CAD applications (OpenCASCADE/pythonOCC) on a headless Linux server with browser-based VNC access. Perfect for remote 3D CAD operations with a full graphical interface.

---

## 🚀 Quick Setup (Recommended)

Follow these steps for a fast and reliable setup:

### 1. Install X11 and VNC Requirements

```bash
sudo apt update
sudo apt install xfce4 xfce4-goodies xorg dbus-x11 x11-xserver-utils
sudo apt install x11vnc websockify
```

### 2. Set Up noVNC

```bash
git clone https://github.com/novnc/noVNC.git ~/noVNC
cd ~/noVNC
git submodule update --init --recursive
x11vnc -storepasswd
```

### 3. Reset/Clean Up Existing VNC/X11 Processes (if needed)

```bash
# Check what's currently running
ps aux | grep -E "(Xvfb|x11vnc|novnc|xfce)" | grep -v grep

# Check what ports are occupied
sudo netstat -tlnp | grep -E "(590|608)"

# Kill everything VNC related
sudo pkill -f Xvfb
sudo pkill -f x11vnc
sudo pkill -f novnc
sudo pkill -f xfce4-session
sleep 3
```

### 4. Run the Startup Script

```bash
./start_vnc.sh
```

### 5. Access the Desktop

- Open your browser and go to: `http://YOUR_SERVER_IP:6080/vnc.html`
- Enter your VNC password when prompted

#### (Optional) Check if anything is still running

```bash
ps aux | grep -E "(Xvfb|x11vnc|novnc|xfce)" | grep -v grep
```

---

## 🛠️ Advanced/Manual Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd step-parser-repo
```

### 2. Install System Dependencies

```bash
# Update package list
sudo apt update

# Install required packages for VNC and X11
sudo apt install -y \
    xvfb \
    x11vnc \
    xfce4 \
    xfce4-goodies \
    xorg \
    dbus-x11 \
    x11-xserver-utils \
    git \
    curl \
    python3 \
    python3-pip

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 3. Install noVNC

```bash
# Clone noVNC repository
cd ~
git clone https://github.com/novnc/noVNC.git
cd noVNC
git submodule update --init --recursive
```

### 4. Set Up VNC Password

```bash
# Set a VNC password (you'll be prompted to enter one)
x11vnc -storepasswd
```

### 5. Automated Startup Script (Alternative)

Create the startup script:

```bash
cat > start_vnc.sh << 'EOF'
#!/bin/bash
# CAD Runner VNC Startup Script

echo "🚀 Starting CAD Runner VNC Services..."

# Clean up existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f Xvfb; pkill -f x11vnc; pkill -f novnc; pkill -f xfce4-session
sleep 2

# Start virtual display
echo "🖥️  Starting virtual display..."
Xvfb :1 -screen 0 1280x800x24 &
sleep 3

# Start desktop environment
echo "🖥️  Starting desktop environment..."
export DISPLAY=:1
xfce4-session &
sleep 3

# Start VNC server
echo "🔗 Starting VNC server..."
x11vnc -display :1 -forever -shared -rfbport 5900 &
sleep 3

# Start noVNC web interface
echo "🌐 Starting noVNC web interface..."
cd ~/noVNC
./utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080 &
sleep 2

# Get public IP and display access information
PUBLIC_IP=$(curl -s ifconfig.me)
echo ""
echo "✅ Services started successfully!"
echo "🌐 Access your desktop at: http://$PUBLIC_IP:6080/vnc.html"
echo ""
echo "📊 Services running:"
ps aux | grep -E "(Xvfb|x11vnc|novnc)" | grep -v grep
echo ""
echo "🔧 To stop services: pkill -f 'Xvfb|x11vnc|novnc'"
EOF

chmod +x start_vnc.sh
```

Run the startup script:

```bash
./start_vnc.sh
```

### 6. Manual Startup (Alternative)

```bash
# Start virtual display
Xvfb :1 -screen 0 1280x800x24 &
export DISPLAY=:1

# Start desktop environment
xfce4-session &

# Start VNC server
x11vnc -display :1 -forever -shared -rfbport 5900 &

# Start noVNC web interface
cd ~/noVNC
./utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080 &
```

---

## 🌐 Accessing the Desktop

1. **Get your server's public IP:**
   ```bash
   curl ifconfig.me
   ```
2. **Open your web browser and navigate to:**
   ```
   http://YOUR_SERVER_IP:6080/vnc.html
   ```
3. **Enter your VNC password** when prompted

---

## 🐳 Docker Application Setup

### 1. Create Docker Network

```bash
docker network create cad-net
```

### 2. Build and Run the CAD Application

```bash
# Build the Docker image
docker-compose build

# Run the application
docker-compose up -d
```

### 3. Access the CAD API

The CAD application will be available at:

```bash
docker exec -it cad-runner bash
```



docker run -d \
  --name cad-runner \
  --platform linux/amd64 \
  --network host \
  -v /root/step-parser-repo:/app \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /root/.Xauthority:/root/.Xauthority:ro \
  -e DISPLAY=:1 \
  -e XAUTHORITY=/root/.Xauthority \
  --security-opt seccomp=unconfined \
  --cap-add=SYS_PTRACE \
  unifest/step-parser-repo:latest


docker-compose pull         # This pulls the image from Docker Hub
docker-compose up -d  


docker compose down
docker system prune --all --volumes -f



test.sh file: 

#!/bin/bash                                                                                 
# Set display
export DISPLAY=:1

# Test display
echo "Testing display..."
xdpyinfo > /tmp/xdpyinfo.log 2>&1
cat /tmp/xdpyinfo.log

# Start VNC
echo "Starting x11vnc..."
x11vnc -display :1 -forever -shared -rfbport 5900 > /tmp/x11vnc.log 2>&1 &
sleep 3

# Check VNC
echo "Checking x11vnc status..."
ps aux | grep x11vnc | grep -v grep

# Test connection
echo "Testing VNC connection..."
telnet localhost 5900 < /dev/null

echo "=== Debug Complete ==="
echo "Xvfb log: cat /tmp/xdpyinfo.log"
echo "x11vnc log: cat /tmp/x11vnc.log"