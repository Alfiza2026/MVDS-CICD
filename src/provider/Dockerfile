FROM python:3.11-slim

WORKDIR /app

COPY app.py .

RUN pip install flask requests prometheus_client --no-cache-dir

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

CMD ["python", "app.py"]
