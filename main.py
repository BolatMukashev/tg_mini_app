from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import json
from ydb_connect import save_to_cache

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def mini_app(request: Request):
    """
    Telegram Mini App открывает этот URL.
    Telegram автоматически передаёт initData через Telegram.WebApp.initData.
    start_param можно достать из Telegram.WebApp.initDataUnsafe.start_param
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/save_ref")
async def save_ref(request: Request):
    data = await request.json()
    tg_id = data.get("tg_id")
    ref = data.get("ref")
    await save_to_cache(tg_id, "referal", ref)
    print(f"📥 Новый переход: user_id={tg_id}, ref={ref}")
    return {"status": "ok"}

@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.ico")
