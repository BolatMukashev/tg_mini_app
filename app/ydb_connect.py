import ydb
import ydb.aio
import asyncio
from typing import Optional, Dict, Any
from app.config import YDB_ENDPOINT, YDB_PATH, YDB_TOKEN
from dataclasses import dataclass


# yc iam create-token   (12 часов действует)


# ------------------------------------------------------------ Базовый класс -----------------------------------------------------------


class YDBClient:
    def __init__(self, endpoint: str = YDB_ENDPOINT, database: str = YDB_PATH, token: str = YDB_TOKEN):
        """
        Инициализация клиента YDB
        """
        self.endpoint = endpoint
        self.database = database
        self.token = token
        self.driver = None
        self.pool = None
        self.credentials = ydb.AccessTokenCredentials(self.token) #ydb.iam.MetadataUrlCredentials() #
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
    
    async def connect(self):
        """
        Создание соединения с YDB и инициализация пула сессий
        """
        if self.driver is not None:
            return  # уже подключены
            
        driver_config = ydb.DriverConfig(
            self.endpoint, 
            self.database,
            credentials=self.credentials,
            root_certificates=ydb.load_ydb_root_certificate(),
        )
        
        self.driver = ydb.aio.Driver(driver_config)
        
        try:
            await self.driver.wait(timeout=5)
            self.pool = ydb.aio.QuerySessionPool(self.driver)
            print("Successfully connected to YDB")
        except TimeoutError:
            print("Connect failed to YDB")
            print("Last reported errors by discovery:")
            print(self.driver.discovery_debug_details())
            await self.driver.stop()
            self.driver = None
            raise
    
    async def close(self):
        """
        Закрытие соединения с YDB
        """
        if self.pool:
            await self.pool.stop()
            self.pool = None
        
        if self.driver:
            await self.driver.stop()
            self.driver = None
            print("YDB connection closed")
    
    def _ensure_connected(self):
        """
        Проверка, что соединение установлено
        """
        if self.driver is None or self.pool is None:
            raise RuntimeError("YDB client is not connected. Call connect() first or use as async context manager.")
    
    async def table_exists(self, table_name: str) -> bool:
        """
        Проверка существования таблицы
        """
        self._ensure_connected()
        try:
            await self.pool.execute_with_retries(f"SELECT 1 FROM `{table_name}` LIMIT 0;")
            return True
        except ydb.GenericError:
            return False
    
    async def create_table(self, table_name: str, schema: str):
        """
        Создание таблицы с заданной схемой (если она не существует)
        """
        self._ensure_connected()
        print(f"\nChecking if table {table_name} exists...")
        try:
            await self.pool.execute_with_retries(schema)
            print(f"Table {table_name} created successfully!")
        except ydb.GenericError as e:
            if "path exist" in str(e):
                print(f"Table {table_name} already exists, skipping creation.")
            else:
                raise e
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        Выполнение произвольного запроса
        """
        self._ensure_connected()
        return await self.pool.execute_with_retries(query, params)
    
    async def clear_all_tables(self):
        """Удаляет все записи во всех таблицах"""
        self._ensure_connected()

        tables = [
            "cache",
        ]

        for table in tables:
            try:
                await self.execute_query(f"DELETE FROM `{table}`;")
                print(f"Таблица {table} очищена.")
            except Exception as e:
                print(f"Ошибка при очистке {table}: {e}")


async def clear_cache():
    async with YDBClient() as client:
        await client.clear_all_tables()


# ------------------------------------------------------------ КЭШ -----------------------------------------------------------


@dataclass
class Cache:
    telegram_id: int = None
    parameter: Optional[str] = None
    value: Optional[int] = None


class CacheClient(YDBClient):
    def __init__(self, endpoint: str = YDB_ENDPOINT, database: str = YDB_PATH, token: str = YDB_TOKEN):
        super().__init__(endpoint, database, token)
        self.table_name = "cache"
        self.table_schema = """
            CREATE TABLE `cache` (
                `telegram_id` Uint64 NOT NULL,
                `parameter` Utf8,
                `value` Uint64,
                PRIMARY KEY (`telegram_id`, `parameter`)
            )
        """
    
    async def insert_cache(self, cache: Cache) -> Cache:
        """
        Вставка записи в кэш
        """
        await self.execute_query(
            """
            DECLARE $telegram_id AS Uint64;
            DECLARE $parameter AS Utf8?;
            DECLARE $value AS Uint64?;

            UPSERT INTO cache (telegram_id, parameter, value)
            VALUES ($telegram_id, $parameter, $value);
            """,
            self._to_params(cache)
        )

    # --- helpers ---
    def _row_to_cache(self, row) -> Cache:
        return Cache(
            telegram_id=row["telegram_id"],
            parameter=row.get("parameter"),
            value=row.get("value"),
        )

    def _to_params(self, cache: Cache) -> dict:
        return {
            "$telegram_id": (cache.telegram_id, ydb.PrimitiveType.Uint64),
            "$parameter": (cache.parameter, ydb.OptionalType(ydb.PrimitiveType.Utf8)),
            "$value": (cache.value, ydb.OptionalType(ydb.PrimitiveType.Uint64)),
        }


async def save_to_cache(telegram_id, parameter, value):
    async with CacheClient() as client:
        new_cache = Cache(telegram_id, parameter, value)
        await client.insert_cache(new_cache)


# ------------------------------------------------------------ ДОНАТ КОМПАНИИ -----------------------------------------------------------


@dataclass
class DonateCompany:
    telegram_id: int
    first_name: Optional[str] = None
    photo_id: Optional[str] = None
    about_company: Optional[str] = None
    link_text: Optional[str] = None
    ref_code: Optional[str] = None
    prices: Optional[str] = None


class DonateCompanyClient(YDBClient):
    def __init__(self, endpoint: str = YDB_ENDPOINT, database: str = YDB_PATH, token: str = YDB_TOKEN):
        super().__init__(endpoint, database, token)
        self.table_name = "donate_companies"
        self.table_schema = """
            CREATE TABLE `donate_companies` (
                `telegram_id` Uint64 NOT NULL,
                `first_name` Utf8,
                `photo_id` Utf8,
                `about_company` Utf8,
                `link_text` Utf8,
                `ref_code` Utf8,
                `prices` Utf8,
                PRIMARY KEY (`telegram_id`)
            )
        """
      
    async def get_id_by_ref_code(self, ref_code: str) -> Optional[int]:
        """Получение telegram_id по ref_code"""
        result = await self.execute_query(
            """
            DECLARE $ref_code AS Utf8;

            SELECT telegram_id
            FROM donate_companies
            WHERE ref_code = $ref_code;
            """,
            {"$ref_code": (ref_code, ydb.PrimitiveType.Utf8)}
        )

        rows = result[0].rows
        if not rows:
            return None

        return rows[0]["telegram_id"]

    def _row_to_company(self, row) -> DonateCompany:
        return DonateCompany(
            telegram_id=row["telegram_id"],
            first_name=row.get("first_name"),
            photo_id=row.get("photo_id"),
            about_company=row.get("about_company"),
            link_text=row.get("link_text"),
            ref_code=row.get("ref_code"),
            prices=row.get("prices"),
        )

    def _to_params(self, donate_company: DonateCompany) -> dict:
        return {
            "$telegram_id": (donate_company.telegram_id, ydb.PrimitiveType.Uint64),
            "$first_name": (donate_company.first_name, ydb.OptionalType(ydb.PrimitiveType.Utf8)),
            "$photo_id": (donate_company.photo_id, ydb.OptionalType(ydb.PrimitiveType.Utf8)),
            "$about_company": (donate_company.about_company, ydb.OptionalType(ydb.PrimitiveType.Utf8)),
            "$link_text": (donate_company.link_text, ydb.OptionalType(ydb.PrimitiveType.Utf8)),
            "$ref_code": (donate_company.ref_code, ydb.OptionalType(ydb.PrimitiveType.Utf8)),
            "$prices": (donate_company.prices, ydb.OptionalType(ydb.PrimitiveType.Utf8))
        }
    

async def get_id_by_ref(value):
    async with DonateCompanyClient() as client:
        res = await client.get_id_by_ref_code(value)
        return res


# ------------------------------------------------------------------------------------------------------------------------------------------


if __name__ == "__main__":
    asyncio.run(clear_cache())

