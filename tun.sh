#!/bin/bash

CORE_V4_IP=$(cat /app/config/config.json | jq -r ".CORE_V4_IP") 

DOCKER_CONTAINER_KNOWN_HOSTS=/app/ssh/known_hosts

DOCKER_CONTAINER_SSH_KEYS=/app/ssh/id_rsa

CORE_V4_PORT=11000 

LEDSIGN_PORT=80

CORE_V4_HOST=sce@${CORE_V4_IP}

open_ssh_tunnel () {

    ssh -v \
    -o UserKnownHostsFile=${DOCKER_CONTAINER_KNOWN_HOSTS} \
    -o StrictHostKeyChecking=no \
    -i ${DOCKER_CONTAINER_SSH_KEYS} \
    -f -g -N -R 0.0.0.0:${CORE_V4_PORT}:localhost:${LEDSIGN_PORT} ${CORE_V4_HOST}
}

ls /app
ls /app/ssh
echo "here"

chmod 600 ${DOCKER_CONTAINER_SSH_KEYS}

open_ssh_tunnel

python /app/alerting.py 
python /app/server.py

