import argparse
from flask import Flask, request, jsonify, render_template
from os import sep, path
from prometheus_client import Gauge, generate_latest
import random
import subprocess
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo 

from subprocess import Popen, PIPE, STDOUT

from sign_message import SignMessage

proc = None
sign_message = None

threadExists = False
cancel_event = threading.Event()

def turnOff():
    global proc
    global sign_message
    if args.development:
      sign_message = None
    if proc != None:
        proc.kill()
        sign_message = None



app = Flask(__name__)
parser = argparse.ArgumentParser()
parser.add_argument(
    '--development',
    action='store_true',
    help='if set, runs in dev mode (skip ssh tunnel and running binary file)',
)
parser.add_argument(
    '--port',
    type=int,
    default=80,
    help='port for server to listen on',
)
args = parser.parse_args()

last_health_check_request = Gauge(
    'last_health_check_request',
    'the last time the server recieved an HTTP GET request to /api/health-check',
)
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
        if not last_health_check_request._value.get():
            continue
        if now_epoch_seconds - last_health_check_request._value.get() > 120:
            ssh_tunnel_last_opened.set(now_epoch_seconds)
            subprocess.Popen(
                './tun.sh tunnel-only',
                shell=True,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )


@app.route("/api/health-check", methods=["GET"])
def health_check():
    last_health_check_request.set(int(time.time()))
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
    turnOff()
    return jsonify({
        "success": True
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
            command = sign_message.to_subprocess_command()
            print("running command", command, flush=True)
            if not args.development:
                proc = subprocess.Popen(command)
            
        success = True
        return jsonify({
            "success": success
        })
    except Exception as e:
        print(e, flush=True)
        sign_message = None
        return "Could not update sign", 500
    

    
@app.route("/set-time", methods=["GET"])
def setTime():
    global threadExists
    global cancel_event

    if sign_message == None:
        return jsonify({
            "Sign": "Already Expired"
        })
    if request.args.get("endTime") == '':
        return jsonify({
            "Sign": "Never Expires"
        })
    print("TIE CALLED AND ORIENTATION IS TOMORROW!!!!!", flush=True)

    format_code = "%Y-%m-%dT%H:%M"
    endTime = datetime.strptime(request.args.get("endTime"), format_code)
    endTime = endTime.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
    currDate = datetime.now(ZoneInfo("America/Los_Angeles"))
    print(currDate)
    print(endTime)

    ts = abs((endTime - currDate).total_seconds())

    if threadExists:
         print("canceleddd", flush=True)
         cancel_event.set()
         cancel_event = threading.Event()

    currThread = threading.Thread(target=expire, args=(ts,))
    
    currThread.start()
    threadExists = True

    return jsonify({
        "endTime": endTime,
        "today": currDate,
        "time": ts
    })

def expire(exp):
    print("expire called with a timeout of", exp, flush=True)
    if cancel_event.wait(timeout=exp):
        print("forget it lol", flush=True)
        return
    print("untied lmao", flush=True)
    turnOff()


@app.route('/')
def home():       
   return render_template('index.html')


if __name__ == "__main__":
    # give the last opened an initial value of now,
    # since upon starting the led sign the tunnel should
    # be open
    ssh_tunnel_last_opened.set(int(time.time()))
    if not args.development:
        t = threading.Thread(
            target=maybe_reopen_ssh_tunnel,
            daemon=True,
        )
        t.start()
    app.run(host="0.0.0.0", port=args.port, debug=True, threaded=True)
