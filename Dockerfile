FROM python:3.11.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY earthquake/ ./earthquake/
USER 65534:65534
CMD ["python", "-m", "earthquake.verify"]
