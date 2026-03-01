FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r django-group && useradd -r -g django-group django-user

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=django-user:django-group . /app/

RUN mkdir -p /app/staticfiles /app/media /app/data && \
    chown -R django-user:django-group /app && \
    chmod +x /app/entrypoint.sh

USER django-user

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "config.wsgi:application"]
