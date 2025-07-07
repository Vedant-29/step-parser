FROM condaforge/mambaforge:latest

# Set environment variables to prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

WORKDIR /app

# Install system dependencies for headless rendering
RUN apt-get update && apt-get install -y \
    tzdata \
    xvfb \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    libxrender1 \
    libxext6 \
    libx11-6 \
    libxss1 \
    libgconf-2-4 \
    libxtst6 \
    libxi6 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    rm -rf /var/lib/apt/lists/*

# Copy environment first to leverage Docker layer caching
COPY environment.yml .

# Install environment
RUN mamba env create -f environment.yml && \
    conda clean -afy

# Copy source files
COPY . .

# Make the startup script executable
RUN chmod +x entrypoint.sh

# Set environment variables for headless rendering
ENV DISPLAY=:99
ENV QT_X11_NO_MITSHM=1
ENV XVFB_WHD="1920x1080x24"

# Use bash as entrypoint
ENTRYPOINT ["./entrypoint.sh"]