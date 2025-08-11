#!/bin/bash

CORE_V4_IP=$(cat /app/config/config.json | jq -r ".CORE_V4_IP") 

DOCKER_CONTAINER_KNOWN_HOSTS=/app/ssh/known_hosts

DOCKER_CONTAINER_SSH_KEYS=/app/ssh/id_rsa

CORE_V4_PORT=10000 

LEDSIGN_PORT=10000

CORE_V4_HOST=sce@${CORE_V4_IP}

open_ssh_tunnel () {
    echo "running command"
    echo "ssh \
    -o UserKnownHostsFile=${DOCKER_CONTAINER_KNOWN_HOSTS} \
    -o StrictHostKeyChecking=no \
    -i ${DOCKER_CONTAINER_SSH_KEYS} \
    -f -g -N -R 0.0.0.0:${CORE_V4_PORT}:localhost:${LEDSIGN_PORT} ${CORE_V4_HOST}"
    ssh \
    -o UserKnownHostsFile=${DOCKER_CONTAINER_KNOWN_HOSTS} \
    -o StrictHostKeyChecking=no \
    -i ${DOCKER_CONTAINER_SSH_KEYS} \
    -f -g -N -R 0.0.0.0:${CORE_V4_PORT}:localhost:${LEDSIGN_PORT} ${CORE_V4_HOST}
}

ls /app
ls /app/ssh

chmod 600 ${DOCKER_CONTAINER_SSH_KEYS}

open_ssh_tunnel

# if no value is sent along with the invocation of the script,
# run the server. otherwise just open the ssh tunnel. i.e.
#
# to open the tunnel and start the server:
# $ ./tun.sh 
#
# to only open the tunnel:
# $ ./tun.sh tunnel-only
if [ -z "$1" ]
then
    python /app/server.py
fi

