FROM python:3.10.4-alpine

EXPOSE 80

CMD ["python", "-m", "http.server", "80"]