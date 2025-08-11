import argparse
import datetime
import dataclasses
import logging
import os
import subprocess
import threading

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.staticfiles import StaticFiles
import prometheus_client
import uvicorn


logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)

WORKING_DIRECTORY = os.path.dirname(os.path.abspath(__file__))


@dataclasses.dataclass
class SignData:
    # we are using camel case over snake case to match the
    # casing that the SCE website expects. by doing this
    # we skip the need to convert an object's snake case
    # to camel case and vice versa.
    backgroundColor: str
    textColor: str
    borderColor: str
    scrollSpeed: int
    brightness: int
    text: str
    expiration: datetime.datetime

    def to_subprocess_command(self) -> str:
        return [
            os.path.join(WORKING_DIRECTORY, "sce_sign.exe"),
            "--set-speed",
            str(self.scrollSpeed) + " px/vsync",
            "--set-background-color",
            self.backgroundColor[1:],
            "--set-font-color",
            self.textColor[1:],
            "--set-border-color",
            self.borderColor[1:],
            "--set-font-filename",
            os.path.join(WORKING_DIRECTORY, "10x20.bdf"),
            "--set-brightness",
            str(self.brightness) + "%",
            "--set-text",
            self.text,
        ]


app = FastAPI()
cancel_event = threading.Event()
sign_lock = threading.Lock()


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="optional host argument to uvicorn, defaults to 0.0.0.0",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=10000,
        help="port for server to be hosted on, defaults to 10000",
    )
    parser.add_argument(
        "--development", action="store_true", help="stores true if passed in"
    )
    return parser.parse_args()


args = get_args()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03dZ %(threadName)s %(levelname)s:%(filename)s:%(lineno)d: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

sign_data = None
process = None

# when u call replace on a datetime.datetime object, the time technically stays the same
# u are just updating the timezone
# when u call astimezone u are updating the timezone and converting the time to be in that timezone


def set_and_reset_event():
    global cancel_event
    cancel_event.set()
    cancel_event = threading.Event()


def stop_process_and_clear_state():
    global process
    global sign_data

    sign_data = None
    if process is None:
        message = "process is None, skipping termination"
        if args.development:
            message = "running in development mode, skipping termination"
        logging.info(message)
        sign_lock.release()
        return

    # better wording for printing the returncode, if the process
    # was already stopped for some reason we wil log it as such
    exited_text = "already exited"
    if process.poll() is None:  # still running
        exited_text = "exited"
        logging.info(f"Got cancel signal, attempting to terminate PID {process.pid}")
        try:
            process.terminate()  # graceful shutdown
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logging.warning(
                    f"PID {process.pid} did not terminate in time, killing..."
                )
                process.kill()
                process.wait(timeout=5)
        except Exception:
            logging.exception(f"Error stopping process {process.pid}:")

    logging.info(f"Process {process.pid} {exited_text} with code {process.returncode}")
    process = None
    sign_lock.release()


def write_message_to_sign(new_data):
    global process
    global sign_data
    maybe_seconds = None
    maybe_suffix = ""
    if new_data.expiration is not None:
        maybe_seconds = (
            new_data.expiration - datetime.datetime.now(tz=datetime.timezone.utc)
        ).total_seconds()
        maybe_suffix = f", expiring in {maybe_seconds} seconds"
    set_and_reset_event()
    sign_lock.acquire()
    logging.info(f"Updating sign with state {new_data}" + maybe_suffix)
    if not args.development:
        logging.info(
            "starting sign process with command "
            + " \\\n\t".join(new_data.to_subprocess_command())
        )
        process = subprocess.Popen(
            args=new_data.to_subprocess_command(),
            shell=True,
        )
        logging.info(f"sign process started with pid {process.pid}")

    sign_data = new_data

    # https://www.youtube.com/watch?v=a7fH15f-XIU
    # we wait for the event to be set. if/when it is
    # the process is stopped underneath the if statement
    if cancel_event.wait(timeout=maybe_seconds):
        logging.info("recieved cancel signal, exiting now")
    stop_process_and_clear_state()


@app.get("/turn-off")  #
def turn_off_process():
    set_and_reset_event()
    return {"success": True}


@app.post("/update-sign")
async def update(request: Request):
    json_data = await request.json()

    missing_entries = []
    for key in [
        "backgroundColor",
        "textColor",
        "borderColor",
        "scrollSpeed",
        "brightness",
        "text",
    ]:
        if json_data.get(key) is None:
            missing_entries.append(key)

    if missing_entries:
        missing_entries_str = ",".join(missing_entries)
        raise HTTPException(
            status_code=400,
            detail=f"the following parameter(s) are required: {missing_entries_str}",
        )

    new_data = SignData(
        # we have to convert "#FFFFFF" to FFFFFF
        json_data.get("backgroundColor"),
        json_data.get("textColor"),
        json_data.get("borderColor"),
        json_data.get("scrollSpeed"),
        json_data.get("brightness"),
        json_data.get("text"),
        None,
    )
    if json_data.get("expiration") is not None:
        expiration = json_data.get("expiration")
        try:
            expiration_as_dt = datetime.datetime.fromisoformat(
                expiration.replace("Z", "+00:00")
            )
            expiration_as_dt = expiration_as_dt.astimezone(tz=datetime.timezone.utc)
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            if expiration_as_dt < now:
                raise HTTPException(
                    status_code=400,
                    detail=f"expiration value {expiration_as_dt} is before current time of {now}",
                )

            new_data.expiration = expiration_as_dt
        except ValueError as e:
            logging.exception(f"unable to parse expiration {expiration}:")
            raise HTTPException(
                status_code=400,
                detail=f"unable to parse expiration {expiration}: {e.with_traceback}",
            )
    signThread = threading.Thread(target=write_message_to_sign, args=(new_data,))
    signThread.start()

    return {"success": True}


@app.get("/health-check")  # my health check
def status():
    if sign_data is None:
        return {}
    # the below dataclasses.asdict is the equivalent of doing
    # { ...sign_data } in js
    response = {**dataclasses.asdict(sign_data)}
    if process is not None:
        response["pid"] = process.pid
    return response


@app.get("/metrics")
def get_metrics():
    return Response(
        media_type="text/plain",
        content=prometheus_client.generate_latest(),
    )


@app.on_event("shutdown")
def signal_handler():
    set_and_reset_event()


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("server:app", host=args.host, port=args.port, reload=True)
