# CAD Runner with Browser-Based VNC Desktop

This project provides a complete setup for running CAD applications (OpenCASCADE/pythonOCC) on a headless Linux server with browser-based VNC access. Perfect for running 3D CAD operations remotely with full graphical interface access.

## 🚀 Features

- **Browser-based VNC Desktop**: Access a full Linux desktop environment from any web browser
- **CAD Application Support**: Built-in support for OpenCASCADE/pythonOCC for 3D CAD operations
- **Docker Integration**: Containerized application with proper networking
- **STEP File Processing**: Parse and render STEP files with detailed topology analysis
- **RESTful API**: HTTP endpoints for CAD operations
- **Real-time Rendering**: 3D model visualization and rendering capabilities

## 📋 Prerequisites

- Ubuntu 20.04+ server (tested on DigitalOcean droplets)
- Root or sudo access
- At least 2GB RAM (4GB recommended)
- Docker and Docker Compose installed

## ��️ Installation

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

## 🚀 Quick Start

### Option 1: Automated Startup Script

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
echo "��️  Starting virtual display..."
Xvfb :1 -screen 0 1280x800x24 &
sleep 3

# Start desktop environment
echo "��️  Starting desktop environment..."
export DISPLAY=:1
xfce4-session &
sleep 3

# Start VNC server
echo "🔗 Starting VNC server..."
x11vnc -display :1 -forever -shared -rfbport 5900 &
sleep 3

# Start noVNC web interface
echo "�� Starting noVNC web interface..."
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

### Option 2: Manual Startup

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

## �� Docker Application Setup

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