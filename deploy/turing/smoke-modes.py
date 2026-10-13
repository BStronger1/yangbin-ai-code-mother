"""Exercise the retained multi-file and Vue generation modes with small synthetic apps."""
import json,time,urllib.parse
from pathlib import Path
import smoke

state=json.loads(smoke.state_path.read_text())
smoke.call("/api/user/login",{"userAccount":state["account"],"userPassword":state["password"]})
results={}
modes={
    "multi_file": "Use MULTI_FILE mode, not Vue or single HTML. Create exactly three separate files index.html, style.css and script.js. Make a tiny blue page headed YANGBIN_MULTI with one counter button. Link the CSS and JS from the HTML. No external libraries or images. Keep total code under 100 lines.",
    "vue_project": "Use VUE_PROJECT mode with Vue 3 and Vite. Create the smallest complete project: package.json with npm run build, index.html, src/main.js, src/App.vue and vite.config.js. Vite base must be './'. A simple blue page headed YANGBIN_VUE with one counter button. No router, TypeScript, external UI library or images. Keep source under 100 lines. Use file tools to create the real files and then exit."
}
for expected,prompt in modes.items():
    aid=smoke.call("/api/app/add",{"initPrompt":prompt})
    app=smoke.call("/api/app/get/vo?id="+str(aid))
    state.setdefault("additional_apps",[]).append({"id":aid,"type":app["codeGenType"]})
    smoke.save_state(state)
    assert app["codeGenType"]==expected,(expected,app["codeGenType"])
    url=smoke.BASE+"/api/app/chat/gen/code?"+urllib.parse.urlencode({"appId":aid,"message":prompt})
    start=time.monotonic()
    with smoke.opener.open(url,timeout=420) as response:
        stream=response.read().decode()
    (smoke.ROOT/"run"/(expected+"-stream.txt")).write_text(stream)
    assert "event:done" in stream.replace(" ",""),stream[-800:]
    deployed=smoke.call("/api/app/deploy",{"appId":aid})
    page=smoke.opener.open(deployed,timeout=30).read().decode()
    assert "<html" in page.lower() or "<!doctype" in page.lower()
    app=smoke.call("/api/app/get/vo?id="+str(aid))
    state["additional_apps"][-1]["deploy_key"]=app["deployKey"]
    state["additional_apps"][-1]["deploy_url"]=deployed
    smoke.save_state(state)
    results[expected]={"generation":True,"build_and_publish":True,"http_preview":True,
                      "seconds":round(time.monotonic()-start,2)}
    (smoke.ROOT/"run/mode-acceptance.json").write_text(json.dumps(results,indent=2))
    print(json.dumps({expected:results[expected]}),flush=True)
