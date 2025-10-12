from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from ydb_connect import save_to_cache, get_id_by_ref
from mangum import Mangum

app = FastAPI()

# Для Cloud Functions статические файлы нужно обрабатывать иначе
# или загружать в Object Storage
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    templates = Jinja2Templates(directory="templates")
except:
    # Если директории нет (в окружении Cloud Functions)
    templates = None


@app.get("/", response_class=HTMLResponse)
async def mini_app(request: Request):
    """
    Telegram Mini App открывает этот URL.
    Telegram автоматически передаёт initData через Telegram.WebApp.initData.
    start_param можно достать из Telegram.WebApp.initDataUnsafe.start_param
    """
    if templates:
        return templates.TemplateResponse("index.html", {"request": request})
    return HTMLResponse("<h1>App is running</h1>")

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

# Создаём handler для Yandex Cloud Functions
handler = Mangum(app, lifespan="off")

# Для локальной разработки
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

