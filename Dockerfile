FROM python:3.8.4-slim-buster


WORKDIR /app

RUN apt-get update && apt-get install jq ssh -y

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt
COPY tun.sh .
COPY ./config/config.json /app/config/ 

COPY *.py ./

RUN chmod +x sce_sign.exe
RUN chmod +x tun.sh
RUN mkdir /app/ssh

EXPOSE 5000

ENTRYPOINT ["/app/tun.sh"]
