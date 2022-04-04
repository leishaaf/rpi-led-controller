FROM python:3.8.4-slim-buster

WORKDIR /app

COPY . .

RUN python3 -m pip install -r requirements.txt

EXPOSE 5000

CMD ["python3", "server.py"]
