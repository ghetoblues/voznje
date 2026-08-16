FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["sh", "-c", "while true; do python main.py || echo \"$(date -Iseconds) run failed\"; echo \"$(date -Iseconds) cycle done\"; sleep 300; done"]
