FROM python:3.13-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY server.py /app/server.py

RUN addgroup -S blogstats \
    && adduser -S -G blogstats blogstats \
    && mkdir -p /data \
    && chown blogstats:blogstats /data

USER blogstats

EXPOSE 8080

CMD ["python", "/app/server.py"]
