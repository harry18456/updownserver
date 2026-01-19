FROM python:3.12-slim

WORKDIR /app

COPY . /app

# Install the package
RUN pip install --no-cache-dir .

# Expose default port
EXPOSE 8000

# Create a volume mount point and set it as working directory
VOLUME /data
WORKDIR /data

# Use ENTRYPOINT so arguments can be passed easily
ENTRYPOINT ["python", "-m", "updownserver"]
CMD []
