# backend/main.py

import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from database import engine
import models

from routers import surveys
from routers import survey_evaluations


def get_allowed_origins():
    origins = os.getenv("FRONTEND_ORIGINS")

    if origins:
        return [
            origin.strip()
            for origin in origins.split(",")
            if origin.strip()
        ]

    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)


def ensure_sqlite_schema():
    with engine.begin() as connection:
        table_info = connection.execute(text("PRAGMA table_info(survey_items)")).fetchall()
        columns = {row[1] for row in table_info}
        if "item_category" not in columns:
            connection.execute(text("ALTER TABLE survey_items ADD COLUMN item_category TEXT"))


ensure_sqlite_schema()

app.include_router(surveys.router)
app.include_router(survey_evaluations.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "time": datetime.now(timezone.utc).isoformat(),
        "openai_api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "allowed_origins": get_allowed_origins(),
    }
