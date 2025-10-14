from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.ydb_connect import save_to_cache, get_id_by_ref
from asgi_correlation_id import CorrelationIdMiddleware
from app.log_middleware import LogMiddleware
from app.logger import logger


app = FastAPI()

app.add_middleware(LogMiddleware)
app.add_middleware(CorrelationIdMiddleware)

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
    logger.info(f"📥 Новый переход: user_id={tg_id}, ref={ref}")
    if ref:
        ref_id = await get_id_by_ref(ref)
        if ref_id is None:
            logger.info(f"📥 Пользователь не найден: ref={ref}")
        else:
            try:
                await save_to_cache(tg_id, "referal", int(ref_id))
                logger.info(f"📥 Новый переход: user_id={tg_id}, ref={ref}")
            except Exception as e:
                logger.error(f"📥 Ошибка сохранения в кэш: {e}")
                
    return {"status": "ok"}


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.ico")


@app.get("/error")
def read_error():
    raise Exception("Error")
