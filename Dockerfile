FROM ubuntu:22.04

# Set up basic environment
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

WORKDIR /app

# Install core system dependencies (incl. latest Mesa)
RUN apt-get update && apt-get install -y \
    wget \
    bzip2 \
    ca-certificates \
    libglib2.0-0 \
    libxext6 \
    libsm6 \
    libxrender1 \
    git \
    build-essential \
    mesa-utils \
    libgl1-mesa-glx \
    libgl1-mesa-dri \
    libglu1-mesa \
    libosmesa6 \
    libosmesa6-dev \
    libx11-6 \
    x11-apps \
    x11-utils \
    xauth \
    # python support (optional: uncomment if not using conda python)
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# (Optional: Add Kisak Mesa PPA for even newer mesa, usually not needed for 22.04)
# RUN apt-get update && apt-get install -y software-properties-common && \
#     add-apt-repository ppa:kisak/turtle && apt-get update && \
#     apt-get install -y mesa-utils libgl1-mesa-glx libgl1-mesa-dri

# --- Install micromamba (recommended for Docker!) ---
ENV MAMBA_ROOT_PREFIX=/opt/conda
ENV PATH=$MAMBA_ROOT_PREFIX/bin:$PATH

RUN wget -O /tmp/micromamba.tar.bz2 "https://micro.mamba.pm/api/micromamba/linux-64/latest" && \
    mkdir -p $MAMBA_ROOT_PREFIX/bin && \
    tar -xvjf /tmp/micromamba.tar.bz2 -C $MAMBA_ROOT_PREFIX/bin --strip-components=1 bin/micromamba && \
    rm /tmp/micromamba.tar.bz2

# Copy your conda environment file (adjust as needed)
COPY environment.yml .

# Create conda environment
RUN micromamba create -y -n membership_transfer -f environment.yml && \
    micromamba clean -a -y

# Set environment for conda
ENV CONDA_DEFAULT_ENV=membership_transfer
ENV PATH /opt/conda/envs/membership_transfer/bin:$PATH

# Copy your code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Set default display (can be changed via docker-compose or at runtime)
ENV DISPLAY=:1

# Use llvmpipe/software rendering
ENV LIBGL_ALWAYS_SOFTWARE=1
ENV MESA_GL_VERSION_OVERRIDE=3.3
ENV GALLIUM_DRIVER=llvmpipe

# Entrypoint (could also use CMD ["python", "your_app.py"])
ENTRYPOINT ["./entrypoint.sh"]