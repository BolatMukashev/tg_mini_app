from dotenv import dotenv_values

config = dotenv_values(".env")


YDB_ENDPOINT = config.get("YDB_ENDPOINT")
YDB_PATH = config.get("YDB_PATH")
YDB_TOKEN = config.get("YDB_TOKEN")