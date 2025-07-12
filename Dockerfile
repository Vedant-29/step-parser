FROM condaforge/mambaforge:latest

# Set timezone and suppress interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

WORKDIR /app

# Install system dependencies for OpenCASCADE rendering + X11 client libraries
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libgl1-mesa-dev \
    libglu1-mesa \
    libglu1-mesa-dev \
    mesa-utils \
    mesa-common-dev \
    libegl1-mesa \
    libegl1-mesa-dev \
    libgbm1 \
    libgbm-dev \
    libosmesa6 \
    libosmesa6-dev \
    libglapi-mesa \
    libxss1 \
    libgconf-2-4 \
    libxtst6 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
    libx11-6 \
    libxrender1 \
    libxext6 \
    libxi6 \
    libxcursor1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxinerama1 \
    libxcb1 \
    x11-apps \
    x11-utils \
    xauth \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy environment first to leverage Docker cache
COPY environment.yml .

# Create Conda environment
RUN mamba env create -f environment.yml && conda clean -afy

# Set environment path
ENV PATH /opt/conda/envs/membership_transfer/bin:$PATH

# Copy source code
COPY . .

# Make startup script executable
RUN chmod +x entrypoint.sh

# DISPLAY will be set via docker-compose environment
ENV DISPLAY=:1

# Force software OpenGL rendering for container compatibility
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV LIBGL_ALWAYS_INDIRECT=1
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV MESA_GLSL_VERSION_OVERRIDE=330
ENV GALLIUM_DRIVER=llvmpipe
ENV GALLIUM_HUD=simple,fps
ENV MESA_LOADER_DRIVER_OVERRIDE=swrast
ENV LIBGL_DEBUG=verbose
ENV EGL_SOFTWARE=1
ENV __GLX_VENDOR_LIBRARY_NAME=mesa
ENV OPENGL_DRIVER=swrast

# Use conda + entrypoint script
ENTRYPOINT ["./entrypoint.sh"]