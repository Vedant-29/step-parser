FROM condaforge/mambaforge:latest

# Set environment variables to prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Kolkata

WORKDIR /app

# Copy environment first to leverage Docker layer caching
COPY environment.yml .

# Install environment
RUN mamba env create -f environment.yml && \
    conda clean -afy

# Copy source files
COPY . .

# Make the startup script executable
RUN chmod +x entrypoint.sh

# Use bash as entrypoint
ENTRYPOINT ["./entrypoint.sh"]