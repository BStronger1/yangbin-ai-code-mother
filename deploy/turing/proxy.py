"""Serve the UI, published apps and streaming API on one origin."""
import os
from pathlib import Path
from urllib.parse import urlsplit
from aiohttp import web, ClientSession, ClientTimeout, ClientError

ROOT = Path(__file__).resolve().parents[2]
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
       "te", "trailer", "transfer-encoding", "upgrade"}

async def session_context(app):
    app["client"] = ClientSession(timeout=ClientTimeout(total=900), auto_decompress=False)
    yield
    await app["client"].close()

async def api(request):
    path = request.path
    if path.startswith("/api/actuator") and path != "/api/actuator/health":
        raise web.HTTPNotFound()
    if not any(path.startswith("/api/" + p) for p in
               ("user/", "app/", "chatHistory/", "static/", "screenshots/", "actuator/health")):
        raise web.HTTPNotFound()
    origin = request.headers.get("Origin")
    if request.method not in ("GET", "HEAD", "OPTIONS") and origin:
        if urlsplit(origin).netloc != request.host:
            raise web.HTTPForbidden()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in HOP | {"host", "content-length", "forwarded", "x-forwarded-host",
                                         "x-forwarded-proto", "x-forwarded-for"}}
    headers["X-Forwarded-Host"] = request.host
    headers["X-Forwarded-Proto"] = request.scheme
    headers["X-Forwarded-For"] = request.remote or "127.0.0.1"
    data = await request.read()
    try:
        async with request.app["client"].request(
                request.method, "http://127.0.0.1:18125" + request.raw_path,
                headers=headers, data=data, allow_redirects=False) as upstream:
            response = web.StreamResponse(status=upstream.status)
            for key, value in upstream.headers.items():
                if key.lower() not in HOP:
                    response.headers.add(key, value)
            response.headers["X-Content-Type-Options"] = "nosniff"
            await response.prepare(request)
            async for chunk in upstream.content.iter_any():
                await response.write(chunk)
            await response.write_eof()
            return response
    except ClientError:
        raise web.HTTPBadGateway(text="Backend is starting. Please try again shortly.")

def safe_file(root, relative):
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise web.HTTPNotFound()
    if target.is_dir():
        target = target / "index.html"
    return target

async def published(request):
    target = safe_file(ROOT / "tmp/code_deploy", request.match_info["path"])
    if not target.is_file():
        raise web.HTTPNotFound()
    if request.path.rstrip("/") == "/dist/" + request.match_info["path"].rstrip("/") and target.name == "index.html":
        if not request.path.endswith("/") and not request.path.endswith("index.html"):
            raise web.HTTPFound(request.path + "/")
    return web.FileResponse(target, headers={"X-Content-Type-Options": "nosniff"})

async def frontend(request):
    target = safe_file(ROOT / "frontend", request.match_info["path"])
    if not target.is_file():
        if Path(request.match_info["path"]).suffix:
            raise web.HTTPNotFound()
        target = ROOT / "frontend/index.html"
    return web.FileResponse(target, headers={"X-Content-Type-Options": "nosniff"})

app = web.Application(client_max_size=2 * 1024 * 1024)
app.cleanup_ctx.append(session_context)
app.router.add_route("*", "/api/{path:.*}", api)
app.router.add_get("/dist/{path:.*}", published)
app.router.add_get("/{path:.*}", frontend)
if __name__ == "__main__":
    web.run_app(app, host=os.environ.get("PUBLIC_BIND", "127.0.0.1"), port=18824, access_log=None)
