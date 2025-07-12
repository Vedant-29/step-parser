FROM condaforge/mambaforge:latest

# Set timezone and suppress interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

WORKDIR /app

# Install system dependencies for OpenCASCADE rendering
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglu1-mesa \
    libx11-6 \
    libgtk-3-0 \
    libxrender1 \
    libxext6 \
    libgdk-pixbuf2.0-0 \
    libxi6 \
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

# Export DISPLAY from host (will be set at runtime)
ENV DISPLAY=$DISPLAY

# Use conda + entrypoint script
ENTRYPOINT ["./entrypoint.sh"]