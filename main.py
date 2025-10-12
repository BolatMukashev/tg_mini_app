import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ydb_connect import save_to_cache, get_id_by_ref
from asgiref.wsgi import WsgiToAsgi

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def mini_app(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/save_ref")
async def save_ref(request: Request):
    data = await request.json()
    tg_id = data.get("tg_id")
    ref = data.get("ref")
    ref_id = await get_id_by_ref(ref)
    if ref_id:
        await save_to_cache(tg_id, "referal", int(ref_id))
    print(f"📥 Новый переход: user_id={tg_id}, ref={ref}")
    return {"status": "ok"}


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.ico")


from asgiref.compatibility import guarantee_single_callable
from asgiref.wsgi import WsgiToAsgi
from urllib.parse import urlencode
import asyncio

# ASGI-адаптер для FastAPI
asgi_app = guarantee_single_callable(app)

async def handler(event, context):
    """HTTP-обработчик для Yandex Cloud Functions"""
    # Преобразуем event -> HTTP-запрос
    path = event.get("path", "/")
    method = event.get("httpMethod", "GET")
    headers = event.get("headers", {})
    body = event.get("body", None)
    query_params = event.get("queryStringParameters", {}) or {}

    # Создаём scope (ASGI протокол)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in headers.items()
        ],
        "query_string": urlencode(query_params).encode(),
        "client": ("", 0),
        "server": ("", 80),
        "scheme": "https",
    }

    # Формируем тело ответа
    response = {}
    body_bytes = body.encode() if isinstance(body, str) else b""

    async def receive():
        return {"type": "http.request", "body": body_bytes}

    async def send(message):
        if message["type"] == "http.response.start":
            response["statusCode"] = message["status"]
            response["headers"] = {k.decode(): v.decode() for k, v in message["headers"]}
        elif message["type"] == "http.response.body":
            response["body"] = message.get("body", b"").decode()

    await asgi_app(scope, receive, send)
    return response

