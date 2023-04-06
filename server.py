from flask import Flask, request, jsonify
from os import sep, path
from prometheus_client import Gauge, generate_latest
import random
import subprocess
import threading
import time
from subprocess import Popen, PIPE, STDOUT

from sign_message import SignMessage

proc = None
sign_message = None
app = Flask(__name__)

neel = Gauge('neel', '1 if up 0 if not')
ssh_tunnel_last_opened = Gauge('ssh_tunnel_last_opened', 'the last time we opened the ssh tunnel')

def hex_to_rgb(hex_value):
    return ",".join([str(int(hex_value[i:i+2], 16)) for i in (0, 2, 4)])

def maybe_reopen_ssh_tunnel():
    """
    if we havent recieved a health check ping in over 1 min then
    we rerun the script to open the ssh tunnel.
    """
    while 1:
        time.sleep(60)
        now_epoch_seconds = int(time.time())
        # skip reopening the tunnel if the value is 0 or falsy
        if not neel._value.get():
            continue
        if now_epoch_seconds - neel._value.get() > 60:
            ssh_tunnel_last_opened.set(now_epoch_seconds)
            subprocess.Popen(
                './tun.sh tunnel-only',
                shell=True,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )


@app.route("/api/health-check", methods=["GET"])
def health_check():
    neel.set(int(time.time()))
    global sign_message
    if sign_message:
        return jsonify(sign_message.to_dict())
    else:
        return jsonify({
            "success": True
        })

@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest()

@app.route("/api/random", methods=["GET"])
def random_message():
    text = subprocess.check_output(
        "sort -R random.txt | head -n1",
        shell=True).decode('utf-8').strip().replace("\\", "")
    text_color = "#%06x" % random.randint(0, 0xFFFFFF)
    background_color = "#%06x" % random.randint(0, 0xFFFFFF)
    border_color = "#%06x" % random.randint(0, 0xFFFFFF)
    return jsonify({
        "scrollSpeed": 10,
        "backgroundColor": background_color,
        "textColor": text_color,
        "borderColor": border_color,
        "text": text,
        "success": True
    })


@app.route("/api/turn-off", methods=["GET"])
def turn_off():
    global proc
    global sign_message
    success = False
    if proc != None:
        proc.kill()
        sign_message = None
        success = True
    return jsonify({
        "success": success
    })


@app.route("/api/update-sign", methods=["POST"])
def update_sign():
    global proc
    global sign_message
    data = request.json
    CURRENT_DIRECTORY = path.dirname(path.abspath(__file__)) + sep
    success = False
    if proc != None:
        proc.kill()
    try:
        if data and len(data):
            sign_message = SignMessage(data)
            proc = subprocess.Popen(sign_message.to_subprocess_command())
        success = True
        return jsonify({
            "success": success
        })
    except Exception as e:
        print(e, flush=True)
        sign_message = None
        return "Could not update sign", 500


if __name__ == "__main__":
    t = threading.Thread(
        target=maybe_reopen_ssh_tunnel,
        daemon=True,
    )
    t.start()
    app.run(host="0.0.0.0", port=80, debug=True, threaded=True)
