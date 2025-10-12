import os
from dotenv import dotenv_values


config = dotenv_values(".env")


YDB_ENDPOINT = os.environ.get("YDB_ENDPOINT") or config.get("YDB_ENDPOINT")
YDB_PATH = os.environ.get("YDB_PATH") or config.get("YDB_PATH")
YDB_TOKEN = os.environ.get("YDB_TOKEN") or config.get("YDB_TOKEN")
