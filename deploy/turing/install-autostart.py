import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[2]
current = subprocess.run(["crontab", "-l"], text=True, capture_output=True)
if current.returncode not in (0, 1):
    raise SystemExit("Unable to read existing crontab")
line = "@reboot /bin/bash " + str(root / "deploy/turing/start.sh") + " >> " + str(root / "logs/boot.log") + " 2>&1"
if line not in current.stdout.splitlines():
    backup = root / "run/crontab.before-yangbin-code"
    if not backup.exists():
        backup.write_text(current.stdout)
        backup.chmod(0o600)
    result = current.stdout.rstrip() + "\n" + line + "\n"
    subprocess.run(["crontab", "-"], input=result.lstrip("\n"), text=True, check=True)
print("User boot entry installed; other entries preserved. Host reboot was not tested.")
