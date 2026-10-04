FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app app
RUN useradd --create-home dots && mkdir /data && chown dots /data
USER dots
ENV DATA_DIR=/data HOST=0.0.0.0
EXPOSE 8000
# Only Caddy can reach this port (it isn't published), so trusting its forwarded headers is safe.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
