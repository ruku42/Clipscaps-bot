import os
import signal
import subprocess
import sys
import time


processes = [
    subprocess.Popen([sys.executable, "-m", "app.bot"]),
    subprocess.Popen([
        sys.executable,
        "-m",
        "uvicorn",
        "app.web:app",
        "--host",
        "0.0.0.0",
        "--port",
        os.getenv("PORT", "10000"),
    ]),
]


def shutdown(signum=None, frame=None):
    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)


try:
    while True:
        if any(process.poll() is not None for process in processes):
            shutdown()
        time.sleep(1)

except KeyboardInterrupt:
    shutdown()
