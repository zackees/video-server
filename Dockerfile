FROM python:3.10.4-alpine

EXPOSE 8080

CMD ["python", "-m", "http.server", "8080"]