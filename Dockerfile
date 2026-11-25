# Optional alternative to systemd: run the app in a container.
#   docker build -t jobtracker .
#   docker run -d --restart unless-stopped -p 8000:8000 --env-file .env \
#              -v "$PWD/data:/app/data" jobtracker
# The database lives in ./data on the host (the volume), so it survives restarts and new images.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "app:app"]
