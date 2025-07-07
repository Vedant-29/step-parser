FROM continuumio/miniconda3

WORKDIR /app

# Copy environment file and create conda environment
COPY environment.yml .
RUN conda env create -f environment.yml

# Make RUN commands use the new environment
SHELL ["conda", "run", "-n", "step-parser", "/bin/bash", "-c"]

# Copy your files
COPY testStep.py .
COPY *.step .

# Set up display for OpenGL (if needed)
ENV DISPLAY=:99

# Run your script directly
CMD ["conda", "run", "-n", "step-parser", "python", "testStep.py", "--input_dir", "/app", "--output_dir", "/app/output"]