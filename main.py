import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import uvicorn

app = FastAPI(title="Todo List API")

# CORS для Postman
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Путь к БД для Render.com
DB_PATH = "/tmp/todo.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        completed BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# Инициализация БД при старте
init_db()

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False

class Task(TaskBase):
    id: int

    class Config:
        from_attributes = True

@app.get("/")
def home():
    return {
        "status": "API работает!",
        "service": "Todo List",
        "endpoints": {
            "GET /tasks": "Получить все задачи",
            "POST /tasks": "Создать задачу",
            "PUT /tasks/{id}": "Обновить задачу",
            "DELETE /tasks/{id}": "Удалить задачу"
        }
    }

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Важно для получения данных как словаря
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    tasks = cursor.fetchall()
    conn.close()
    return [dict(task) for task in tasks]

@app.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskBase):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (title, description, completed) VALUES (?, ?, ?)",
        (task.title, task.description, task.completed)
    )
    conn.commit()
    task_id = cursor.lastrowid
    
    # ВАЖНО: устанавливаем row_factory ПЕРЕД получением данных
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    new_task = cursor.fetchone()
    conn.close()
    
    # Безопасное преобразование в словарь
    if new_task:
        return dict(new_task)
    else:
        raise HTTPException(status_code=404, detail="Задача не найдена после создания")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: TaskBase):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET title = ?, description = ?, completed = ? WHERE id = ?",
        (task.title, task.description, task.completed, task_id)
    )
    conn.commit()
    
    # ВАЖНО: устанавливаем row_factory ПЕРЕД получением данных
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_task = cursor.fetchone()
    conn.close()
    
    if updated_task:
        return dict(updated_task)
    raise HTTPException(status_code=404, detail="Задача не найдена")

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    
    if rows_affected == 0:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"message": f"Задача {task_id} успешно удалена"}