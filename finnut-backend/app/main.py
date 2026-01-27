from fastapi import FastAPI
from app.db import init_db
from app.routers.scholarships import router as scholarships_router

app = FastAPI(title="FINNUT Backend")

# 서버 켤 때 DB 준비
init_db()

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(scholarships_router)
