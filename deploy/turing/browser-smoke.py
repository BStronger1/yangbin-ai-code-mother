import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
settings=json.loads((ROOT/"secrets.json").read_text())
state=json.loads((ROOT/"run/smoke-state.json").read_text())
base="http://"+settings["env"]["PUBLIC_BIND"]+":18824"
out=ROOT/"run/screenshots"
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=settings["runtime"]["chrome"],headless=True,
                               args=["--no-sandbox","--disable-dev-shm-usage"])
    page=browser.new_page(viewport={"width":1440,"height":1000})
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.goto(base+"/user/login",wait_until="networkidle")
    assert "yangbin" in page.title().lower()
    page.locator("input#basic_userAccount").fill(state["account"])
    page.locator("input#basic_userPassword").fill(state["password"])
    page.locator("button[type=submit]").click()
    page.wait_for_url(base+"/",timeout=30000)
    page.wait_for_load_state("networkidle")
    page.screenshot(path=str(out/"home.png"),full_page=True)
    page.goto(base+"/app/chat/"+str(state["app_id"]),wait_until="networkidle")
    page.screenshot(path=str(out/"app.png"),full_page=True)
    page.reload(wait_until="networkidle")
    assert "/user/login" not in page.url
    if state.get("deploy_url"):
        page.goto(state["deploy_url"],wait_until="networkidle")
        assert page.get_by_text("YANGBIN_SMOKE",exact=True).count()>0
        page.screenshot(path=str(out/"generated.png"),full_page=True)
        button=page.locator("button").first
        before=page.locator("body").inner_text()
        button.click()
        page.wait_for_timeout(250)
        after=page.locator("body").inner_text()
        assert before != after,"Generated counter button did not change visible state"
    assert not errors,errors
    result={"browser_login":True,"home":True,"chat_page":True,"page_refresh":True,
            "generated_button":bool(state.get("deploy_url")),"page_errors":errors}
    (ROOT/"run/browser-acceptance.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
    browser.close()
