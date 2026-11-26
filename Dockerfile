# Container for Railway (and any Docker host).
#   docker build -t jobtracker .
#   docker run -d --restart unless-stopped -p 8000:8000 --env-file .env \
#              -v "$PWD/data:/app/data" jobtracker
# The database lives in /app/data, which must be a volume so it survives restarts and new images.
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8000
EXPOSE 8000
# 1 worker + 4 threads keeps memory low; Railway sets $PORT
CMD gunicorn --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT app:app
