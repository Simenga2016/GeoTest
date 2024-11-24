from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psycopg2
from pydantic import BaseModel
from pgrequests import *
import os
# Настройка шаблонов
templates = Jinja2Templates(directory="templates")  # Укажите путь к папке с шаблонами

# Подключение к базе данных
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host="postgres",
            port="5432"
        )
    except psycopg2.Error as e:
        raise RuntimeError("Database connection failed") from e


def execute_query(conn, query, params=None, fetch=False):
    try:
        if params:
            print("Executing query:", query % params)
        else:
            print("Executing query:", query)

        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall() if fetch else None
        conn.commit()
        cursor.close()
        return result
    except psycopg2.Error as e:
        print(e)
        raise HTTPException(status_code=500, detail="Database query failed") from e

conn = get_db_connection()
execute_query(conn, initialization)
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class LimitRequest(BaseModel):
    service_id: str
    allowed_requests: int

class ResetRequest(BaseModel):
    service_id: str
    type: str  # "statistics" или "rules"

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Страница главная с интерфейсом"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/set_limit")
def set_limit(rule: LimitRequest):
    """API-запрос для создания разрешения обращения к серверу, и установления лимита максимальных подключений"""
    key = rule.service_id
    count = rule.allowed_requests
    execute_query(conn, set_limits, (key, count))
    return {"code": 200, "message": "Rule set successfully"}

@app.get("/get_stats")
def get_stats(service_id: str = Query(None)):
    """API-запрос для получения информации о сервисе"""
    if not service_id:
        raise HTTPException(status_code=400, detail="Service ID required")

    result = execute_query(conn, get_status, (service_id,), fetch=True)

    if not result:
        raise HTTPException(status_code=404, detail="No stats found")

    total, used = result[0]
    return {"service_id": service_id, "allowed_requests": total, "used_requests": used}

@app.post("/reset")
def reset(reset_request: ResetRequest):
    """API-запрос для сброса данных сервера или полного удаления сервера"""
    if reset_request.type == "Uses":
        execute_query(conn, stat_reset, (reset_request.service_id,))
        return {"message": f"Uses reset successfully"}

    elif reset_request.type == "Total":
        execute_query(conn, rule_reset, (reset_request.service_id,))
        return {"message": "Total reset successfully"}

    else:
        raise HTTPException(status_code=400, detail="Invalid reset type")
