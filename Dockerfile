FROM continuumio/miniconda3:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

WORKDIR /app

# Install system dependencies for OCC, X11, GL, etc.
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    mesa-utils \
    libegl1-mesa \
    libgbm1 \
    libosmesa6 \
    libosmesa6-dev \
    libx11-6 \
    libgtk-3-0 \
    libxrender1 \
    libxext6 \
    libgdk-pixbuf2.0-0 \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxinerama1 \
    libxcb1 \
    x11-apps \
    x11-utils \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Copy your environment file (YAML format, NOT package_lists.txt)
COPY environment.yml .

# Create conda environment as per your environment.yml
RUN conda env create -f environment.yml

# Make your environment the default
SHELL ["conda", "run", "-n", "membership_transfer", "/bin/bash", "-c"]

# Set environment path (optional: for bash shells)
ENV PATH /opt/conda/envs/membership_transfer/bin:$PATH

# Copy source code
COPY . .

RUN chmod +x entrypoint.sh

ENV DISPLAY=:1
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV GALLIUM_DRIVER=llvmpipe

ENTRYPOINT ["./entrypoint.sh"]