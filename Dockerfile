FROM python:3.13.3-alpine AS builder

ARG ENVIRONMENT
ARG PORT

RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    postgresql-dev \
    build-base

WORKDIR /app

COPY requirements requirements
RUN pip install --no-cache-dir -r requirements/${ENVIRONMENT}.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE ${PORT}

CMD gunicorn --bind ${HOST}:${PORT} --workers 4 --threads 2 app:app