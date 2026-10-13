"""Restart only this application's children and rotate their output."""
import fcntl, json, logging, logging.handlers, os, signal, socket, subprocess, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.umask(0o077)
os.chdir(ROOT)
lock = (ROOT / "run/supervisor.lock").open("w")
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
settings = json.loads((ROOT / "secrets.json").read_text())
env = dict(os.environ, **settings["env"])
runtime = settings["runtime"]
commands = {
    "mysql": ["/usr/sbin/mysqld", "--defaults-file=" + str(ROOT / "mysql.cnf")],
    "redis": [runtime["redis"], str(ROOT / "redis.conf")],
    "backend": [runtime["java"], "-Xms128m", "-Xmx768m", "-Dfile.encoding=UTF-8", "-jar", str(ROOT / "app.jar")],
    "proxy": [str(ROOT / "runtime/venv/bin/python"), str(ROOT / "deploy/turing/proxy.py")]
}
children, retry_at, readers = {}, {}, []
stopping = False

def stop(signum, frame):
    global stopping
    stopping = True

for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, stop)

def consume(name, stream):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.handlers.RotatingFileHandler(ROOT / ("logs/" + name + ".log"),
                                                   maxBytes=5 * 1024 * 1024, backupCount=3)
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    for line in iter(stream.readline, ""):
        logger.info(line.rstrip())
    stream.close()
    logger.removeHandler(handler)
    handler.close()

def ready(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

try:
    while not stopping:
        for name, command in commands.items():
            proc = children.get(name)
            if proc is not None and proc.poll() is None:
                continue
            if proc is not None:
                children.pop(name)
                retry_at[name] = time.time() + 5
            if time.time() < retry_at.get(name, 0):
                continue
            if name == "backend" and not (ready(13308) and ready(16381)):
                continue
            proc = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, errors="replace", start_new_session=True)
            children[name] = proc
            thread = threading.Thread(target=consume, args=(name, proc.stdout), daemon=True)
            thread.start()
        time.sleep(1)
finally:
    for name in ("proxy", "backend", "redis", "mysql"):
        proc = children.get(name)
        if proc and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=45)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()
