"""Small live acceptance test. Creates only a dedicated synthetic account."""
import argparse, http.cookiejar, io, json, os, secrets, time, urllib.request, urllib.parse, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
settings=json.loads((ROOT/"secrets.json").read_text())
BASE="http://"+settings["env"]["PUBLIC_BIND"]+":18824"
state_path=ROOT/"run/smoke-state.json"
cookies=http.cookiejar.LWPCookieJar(str(ROOT/"run/smoke-cookies.txt"))
if Path(cookies.filename).exists(): cookies.load(ignore_discard=True,ignore_expires=True)
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
os.umask(0o077)

def call(path,data=None):
    payload=None if data is None else json.dumps(data).encode()
    req=urllib.request.Request(BASE+path,data=payload,headers={"Content-Type":"application/json"})
    with opener.open(req,timeout=300) as res: out=json.load(res)
    assert out.get("code")==0,(path,out)
    return out["data"]

def save_state(state):
    state_path.write_text(json.dumps(state))
    state_path.chmod(0o600)
    cookies.save(ignore_discard=True,ignore_expires=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--verify",action="store_true")
    args=parser.parse_args()
    if args.verify:
        state=json.loads(state_path.read_text())
        assert str(call("/api/user/get/login")["id"])==str(state["user_id"])
        app=call("/api/app/get/vo?id="+str(state["app_id"]))
        assert app["deployKey"]==state["deploy_key"]
        assert "YANGBIN_SMOKE" in opener.open(state["deploy_url"]).read().decode()
        state["report"]["restart_persistence"]=True
        save_state(state)
        (ROOT/"run/acceptance.json").write_text(json.dumps(state["report"],indent=2))
        print(json.dumps(state["report"]))
        return
    previous=json.loads(state_path.read_text()) if state_path.exists() else {}
    account=previous.get("account") or "qa_"+secrets.token_hex(5)
    password=previous.get("password") or secrets.token_urlsafe(18)
    uid=previous.get("user_id") or call("/api/user/register",{"userAccount":account,"userPassword":password,"checkPassword":password})
    login=call("/api/user/login",{"userAccount":account,"userPassword":password})
    assert str(login["id"])==str(uid)
    state={"account":account,"password":password,"user_id":uid,"report":{"register":True,"login":True}}
    save_state(state)
    prompt="Create a very small single-file HTML page with inline CSS. Heading must be YANGBIN_SMOKE, with a blue card and one working counter button. No external images, dependencies, or frameworks. Keep all code under 80 lines."
    aid=previous.get("app_id") or call("/api/app/add",{"initPrompt":prompt})
    app=call("/api/app/get/vo?id="+str(aid))
    state["app_id"]=aid
    state["code_type"]=app["codeGenType"]
    save_state(state)
    assert state["code_type"]=="html",state["code_type"]
    url=BASE+"/api/app/chat/gen/code?"+urllib.parse.urlencode({"appId":aid,"message":prompt})
    start=time.monotonic()
    chunks=[]
    first=None
    with opener.open(url,timeout=300) as response:
        assert "text/event-stream" in response.headers.get("Content-Type","")
        for raw in response:
            if first is None: first=time.monotonic()-start
            chunks.append(raw.decode())
    stream="".join(chunks)
    assert "event:done" in stream.replace(" ",""),stream[-600:]
    merged="".join(json.loads(line[5:].strip())["d"] for line in stream.splitlines() if line.startswith("data:") and line[5:].strip())
    assert "YANGBIN_SMOKE" in merged,merged[-600:]
    preview="/api/static/html_"+str(aid)+"/"
    html=opener.open(BASE+preview).read().decode()
    assert "YANGBIN_SMOKE" in html
    deploy=call("/api/app/deploy",{"appId":aid})
    assert "YANGBIN_SMOKE" in opener.open(deploy).read().decode()
    payload=opener.open(BASE+"/api/app/download/"+str(aid)).read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        assert any(n.endswith("index.html") for n in archive.namelist())
    cover=""
    for _ in range(40):
        app=call("/api/app/get/vo?id="+str(aid))
        cover=app.get("cover") or ""
        if cover: break
        time.sleep(2)
    assert cover.startswith("/api/screenshots/"),"Screenshot did not finish"
    image=opener.open(BASE+cover).read()
    assert image[:2]==b"\xff\xd8"
    state.update(deploy_url=deploy,deploy_key=app["deployKey"])
    state["report"].update(real_model=settings["env"]["AI_MODEL"],application_create=True,
                           sse_generation=True,preview=True,publish=True,zip_download=True,
                           screenshot=True,first_stream_seconds=round(first,2),generated_bytes=len(html))
    save_state(state)
    (ROOT/"run/acceptance.json").write_text(json.dumps(state["report"],indent=2))
    print(json.dumps(state["report"]))
if __name__=="__main__": main()
