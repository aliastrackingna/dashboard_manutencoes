FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt


FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r django-group && useradd -r -g django-group django-user

COPY --from=builder /root/.local /home/django-user/.local

ENV PATH=/home/django-user/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN mkdir -p /app/staticfiles /app/media

RUN chown -R django-user:django-group /app

USER django-user

COPY --chown=django-user:django-group entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

COPY --chown=django-user:django-group --from=builder /home/django-user/.local/lib/python3.12/site-packages /home/django-user/.local/lib/python3.12/site-packages

COPY --chown=django-user:django-group . /app/

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120", "config.wsgi:application"]
