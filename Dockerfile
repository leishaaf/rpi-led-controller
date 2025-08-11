FROM python:3.8.4-slim-buster


WORKDIR /app

RUN apt-get update && apt-get install jq ssh -y

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt
COPY tun.sh .
COPY ./config/config.json /app/config/ 
COPY sce_sign.exe .

COPY *.py ./


COPY 10x20.bdf .

RUN chmod +x sce_sign.exe
RUN chmod +x tun.sh
RUN mkdir /app/ssh

COPY ./static /app/static

EXPOSE 5000

ENTRYPOINT ["/app/tun.sh"]

