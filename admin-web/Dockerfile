FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends restic ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 2264 webmaster \
    && useradd --system --uid 2264 --gid webmaster --home /nonexistent --shell /usr/sbin/nologin webmaster

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
RUN chmod 0755 /app/entrypoint.sh \
    && mkdir -p /srv/content/posts /srv/content/published/posts /srv/content/trash /srv/generated/releases \
        /srv/media/public /srv/media/staging /srv/media/trash \
        /srv/managed/public /srv/managed/staging /srv/managed/trash /srv/state /srv/backups \
    && DJANGO_DEBUG=1 python manage.py collectstatic --noinput \
    && chown -R webmaster:webmaster /srv

USER webmaster
EXPOSE 8000
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind=0.0.0.0:8000", "--workers=2", "--threads=4", "--timeout=3600", "--no-control-socket", "webmaster.wsgi:application"]
