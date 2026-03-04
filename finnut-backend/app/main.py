from fastapi import FastAPI
from app.db import init_db
from app.routers.scholarships import router as scholarships_router
# ✅ 추가
from app.routers.policies import router as policies_router   
from app.routers.recommendations import router as recommendations_router
from app.routers.users import router as users_router
from app.routers.eligibility import router as eligibility_router
from app.routers.user_recommendations import router as user_recommendations_router

app = FastAPI(title="FINNUT Backend")

# 서버 켤 때 DB 준비
init_db()

@app.get("/health")
def health_check():
    return {"status": "ok"}

app.include_router(scholarships_router)
# ✅ 추가
app.include_router(policies_router)  
app.include_router(recommendations_router)
app.include_router(users_router)
app.include_router(eligibility_router)
app.include_router(user_recommendations_router)

