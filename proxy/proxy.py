import aiohttp
import aiohttp_cors
import asyncio
from aiohttp import web
import psycopg2
from psycopg2.extras import RealDictCursor
import aioredis
import os
# Конфигурация для подключения к базе данных PostgreSQL


DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": "postgres",
    "port": "5432"
}


# Подключение к базе данных PostgreSQL
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Подключение к Redis (асинхронное подключение)
REDIS_HOST = "redis"
REDIS_PORT = 6379
redis_client = None


async def init_redis():
    """Инициализация подключения к Redis."""
    global redis_client
    redis_client = await aioredis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    print("Redis connection established")  # Cообщение о подключении


async def init_redis_from_db():
    """Инициализация данных в Redis на основе содержимого базы данных."""
    cursor.execute("SELECT * FROM limits;")
    rows = cursor.fetchall()
    for row in rows:
        # Добавление данных из базы данных в Redis
        await redis_client.hset(f"rule:{row['server']}", mapping={
            "total": int(row["total"]),
            "used": max(int(row["used"]), 0)
        })


async def fetch_db_values():
    """Асинхронно обновляет данные в Redis с учетом базы данных."""
    while True:
        try:
            cursor.execute("SELECT * FROM limits;")
            rows = cursor.fetchall()
            db_dict = {row['server']: {'total': int(row['total']), 'used': int(row['used'])} for row in rows}

            # Обновление данных в Redis
            for server, db_data in db_dict.items():
                redis_key = f"rule:{server}"
                redis_data = await redis_client.hgetall(redis_key)

                if redis_data:
                    redis_used = int(redis_data.get("used", 0))
                    redis_total = int(redis_data.get("total", 0))

                    # Обновление used
                    if db_data['used'] == -1:
                        await redis_client.hset(redis_key, "used", 0)
                        cursor.execute("UPDATE limits SET used = 0 WHERE server = %s;", (server,))
                    elif db_data['used'] > redis_used:
                        await redis_client.hset(redis_key, "used", db_data['used'])
                    else:
                        await redis_client.hset(redis_key, "used", redis_used)
                        cursor.execute("UPDATE limits SET used = %s WHERE server = %s;", (redis_used, server))

                    # Обновление total
                    if db_data['total'] != redis_total:
                        await redis_client.hset(redis_key, "total", db_data['total'])
                        cursor.execute("UPDATE limits SET total = %s WHERE server = %s;", (db_data['total'], server))

                else:
                    # Если в Redis данных нет, добавляем их из базы данных
                    await redis_client.hset(f"rule:{db_data['server']}", mapping={
                        "total": int(db_data["total"]),
                        "used": max(int(db_data["used"]), 0)
                    })

                    if db_data["used"] == -1:
                        cursor.execute("UPDATE limits SET used = 0 WHERE server = %s;", (server,))
            conn.commit()

        except Exception as e:
            print(f"Ошибка при запросе к БД: {e}")  # Информативное сообщение об ошибке

        await asyncio.sleep(10)



async def handle_get(request):
    """Обработка GET-запросов."""
    target_url = request.path_qs
    if not target_url.startswith("http"):
        target_url = "https://portaltest.gismap.by/" + target_url[1:]

    # Поиск подходящего правила в Redis
    matching_rule = None
    redis_keys = await redis_client.keys("rule:*")
    for key in redis_keys:
        rule = await redis_client.hgetall(key)

        if key.replace('rule:', '') in target_url:
            matching_rule = rule
            break

    if matching_rule:
        # Проверка условия использования
        used = matching_rule.get("used", "0")  # Если "used" нет, по умолчанию 0
        total = matching_rule.get("total", "0")  # Если "total" нет, по умолчанию 0

        if int(used) >= int(total):
            return web.Response(status=403, text=f"Out of requests!")

        # Обновление значения "used" в Redis
        new_used = str(int(used) + 1)
        await redis_client.hset(key, "used", new_used)

    else:
        print("No matching rule found.")  # Сообщение об отсутствии сервера в разрешенных

    # Запрос к целевому URL
    async with aiohttp.ClientSession() as session:
        async with session.get(target_url) as response:
            body = await response.read()
            content_type = response.headers.get("Content-Type", "text/html").split(";")[0]
            return web.Response(
                status=response.status,
                body=body,
                content_type=content_type
            )


async def handle_post(request):
    """Обработка POST-запросов"""
    target_url = "https://portaltest.gismap.by/" + request.path_qs
    if not target_url.startswith("http"):
        target_url = target_url[1:]

    post_data = await request.read()

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(target_url, data=post_data) as response:
                body = await response.read()
                content_type = response.headers.get("Content-Type", "text/html")

                if ";" in content_type:
                    content_type = content_type.split(";")[0]

                return web.Response(
                    status=response.status,
                    body=body,
                    content_type=content_type
                )
        except Exception as e:
            return web.Response(status=500, text=f"Ошибка: {e}")  # Сообщение об ошибке


async def init_app():
    """Инициализация веб-приложения и настройка CORS."""
    app = web.Application()
    app.router.add_get('/{tail:.*}', handle_get)
    app.router.add_post('/{tail:.*}', handle_post)

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*",
        )
    })

    # Применение CORS для всех маршрутов
    for route in app.router.routes():
        cors.add(route)

    return app


async def main():
    """Основная функция для запуска приложения и инициализации Redis."""
    await init_redis()
    await init_redis_from_db()  # Инициализация Redis данными из базы данных
    app = await init_app()
    tasks = [
        asyncio.create_task(web._run_app(app, host="0.0.0.0", port=8080)),
        asyncio.create_task(fetch_db_values())
    ]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        if redis_client:
            redis_client.close()
