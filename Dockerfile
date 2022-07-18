FROM python:3.10.4-alpine

CMD ["python", "-m", "http.server", "8080"]