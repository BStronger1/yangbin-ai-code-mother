"""Initialize only this application's private runtime and data."""
import argparse, json, os, secrets, shutil, socket, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
os.umask(0o077)

def save(path, text):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)

def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)

def read_env(path):
    if path.suffix == ".json":
        values = json.loads(path.read_text())
        return {"LLM_API_KEY": values["MODEL_API_KEY"], "LLM_BASE_URL": values["MODEL_BASE_URL"], "LLM_MODEL": values["CHAT_MODEL"]}
    return {k: v.strip().strip("\"'") for k, v in
            (line.split("=", 1) for line in path.read_text().splitlines()
             if "=" in line and not line.lstrip().startswith("#"))}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-env", type=Path, required=True,
                        help="Existing authorized private env with LLM_API_KEY, LLM_BASE_URL, LLM_MODEL")
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()
    for d in ("data/mysql", "data/redis", "logs", "run", "runtime", "tmp/covers",
              "tmp/code_output", "tmp/code_deploy"):
        (ROOT / d).mkdir(parents=True, exist_ok=True, mode=0o700)
    ROOT.chmod(0o700)
    secrets_path = ROOT / "secrets.json"
    if secrets_path.exists():
        raise SystemExit("Already configured. Use start.sh; secrets are never regenerated automatically.")
    for port in (13308, 16381, 18125, 18824):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1" if port != 18824 else args.bind, port)) == 0:
                raise SystemExit("Port already in use: " + str(port))
    model = read_env(args.model_env)
    assert all(model.get(k) for k in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"))
    runtime = {
        "java": str(HOME / ".local/share/recall-agent/runtime/jre21/bin/java"),
        "node_home": str(HOME / "apps/agent-workbench/runtime/node"),
        "redis": str(HOME / "apps/yangbin-passage/runtime/bin/redis-server"),
        "chrome": str(HOME / "apps/agent-workbench/runtime/browsers/chromium-1194/chrome-linux/chrome")
    }
    for key in ("java", "redis", "chrome"):
        assert Path(runtime[key]).is_file(), "Missing runtime: " + key
    assert (Path(runtime["node_home"]) / "bin/node").is_file()
    python = HOME / ".local/bin/python3.12"
    run([python, "-m", "venv", ROOT / "runtime/venv"])
    run([ROOT / "runtime/venv/bin/pip", "install", "-r", ROOT / "deploy/turing/requirements.txt"])
    db_password, root_password, redis_password = (secrets.token_hex(24) for _ in range(3))
    env = {
        "DB_URL": "jdbc:mysql://127.0.0.1:13308/yangbin_ai_code_mother?useSSL=false&allowPublicKeyRetrieval=true&characterEncoding=UTF-8",
        "DB_USER": "yangbin_code", "DB_PASSWORD": db_password,
        "REDIS_HOST": "127.0.0.1", "REDIS_PORT": "16381", "REDIS_PASSWORD": redis_password,
        "SERVER_ADDRESS": "127.0.0.1", "SERVER_PORT": "18125",
        "AI_API_KEY": model["LLM_API_KEY"], "AI_BASE_URL": model["LLM_BASE_URL"],
        "AI_MODEL": model["LLM_MODEL"], "AI_ROUTING_MODEL": model["LLM_MODEL"],
        "AI_REASONING_MODEL": model["LLM_MODEL"], "STORAGE_TYPE": "local",
        "PUBLIC_BIND": args.bind, "DEPLOY_HOST": "http://" + args.bind + ":18824/dist",
        "CHROME_BINARY": runtime["chrome"],
        "PATH": runtime["node_home"] + "/bin:" + os.environ.get("PATH", "/usr/bin:/bin")
    }
    save(ROOT / "mysql.cnf", f"""[mysqld]
datadir={ROOT}/data/mysql
socket={ROOT}/run/mysql.sock
pid-file={ROOT}/run/mysql.pid
port=13308
bind-address=127.0.0.1
log-error={ROOT}/logs/mysql-error.log
skip-name-resolve
skip-log-bin
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
innodb-buffer-pool-size=128M
innodb-use-native-aio=0
max-connections=40
""")
    save(ROOT / "redis.conf", f"""bind 127.0.0.1
port 16381
protected-mode yes
requirepass {redis_password}
dir {ROOT}/data/redis
appendonly yes
appendfsync everysec
save 900 1
maxmemory 256mb
maxmemory-policy noeviction
""")
    save(ROOT / "mysql-admin.cnf", f"""[client]
user=root
password={root_password}
socket={ROOT}/run/mysql.sock
""")
    save(ROOT / "secrets.json", json.dumps({"env": env, "runtime": runtime}, indent=2))
    if (ROOT / "data/mysql/mysql").exists():
        raise SystemExit("Unexpected existing database; refuse initialization.")
    with (ROOT / "logs/mysql-install.log").open("w") as log:
        run(["mysql_install_db", "--no-defaults", "--datadir=" + str(ROOT / "data/mysql"),
             "--auth-root-authentication-method=normal", "--skip-test-db"], stdout=log, stderr=log)
    with (ROOT / "logs/mysql-bootstrap.log").open("w") as log:
        proc = subprocess.Popen(["/usr/sbin/mysqld", "--defaults-file=" + str(ROOT / "mysql.cnf")],
                                cwd=ROOT, stdout=log, stderr=log)
        try:
            cli = ["mysql", "--no-defaults", "--socket=" + str(ROOT / "run/mysql.sock"), "-u", "root"]
            for _ in range(60):
                if proc.poll() is not None:
                    raise RuntimeError("Database initialization process stopped")
                ready = subprocess.run(cli, input="SELECT 1;", text=True, capture_output=True)
                if ready.returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("Database initialization timed out")
            schema = (ROOT / "sql/create_table.sql").read_text()
            sql = schema + f"""
CREATE USER 'yangbin_code'@'127.0.0.1' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON yangbin_ai_code_mother.* TO 'yangbin_code'@'127.0.0.1';
DELETE FROM mysql.user WHERE User = '';
UPDATE mysql.user SET Password=PASSWORD('{root_password}') WHERE User = 'root';
FLUSH PRIVILEGES;
"""
            run(cli, input=sql, text=True, stdout=log, stderr=log)
        finally:
            proc.terminate()
            proc.wait(timeout=45)
    save(ROOT / "run/configured", "ok\n")
    print(json.dumps({"configured": True, "model": model["LLM_MODEL"], "url": "http://" + args.bind + ":18824"}))

if __name__ == "__main__":
    main()
