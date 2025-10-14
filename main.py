import sys, os
sys.path.append(os.path.dirname(__file__))
import uvicorn
from app.app import app
from app.logger import logger

# uvicorn main:app --reload --port 8000
# ngrok http 8080
# http://127.0.0.1:8080/
# http://127.0.0.1:8080/app?startapp=_tgr_r8Aw3RVlM2Qy

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080"))) # log_config=None

