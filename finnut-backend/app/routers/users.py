import json
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.db import get_conn, now_iso

router = APIRouter(tags=["users"])

class UserCreate(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=120)
    student: Optional[bool] = None
    region: Optional[str] = None
    category_preference: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)

class UserUpdate(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=120)
    student: Optional[bool] = None
    region: Optional[str] = None
    category_preference: Optional[str] = None
    keywords: Optional[List[str]] = None

def _bool_to_int(v: Optional[bool]) -> Optional[int]:
    if v is None:
        return None
    return 1 if v else 0

@router.post("/users")
def create_user(payload: UserCreate) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    ts = now_iso()

    cur.execute("""
        INSERT INTO users (age, student, region, category_preference, keywords_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        payload.age,
        _bool_to_int(payload.student),
        payload.region,
        payload.category_preference,
        json.dumps(payload.keywords, ensure_ascii=False),
        ts,
        ts,
    ))
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {"id": user_id, "created_at": ts}

@router.get("/users/{user_id}")
def get_user(user_id: int) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    r = cur.fetchone()
    conn.close()

    if not r:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": r["id"],
        "age": r["age"],
        "student": (None if r["student"] is None else bool(r["student"])),
        "region": r["region"],
        "category_preference": r["category_preference"],
        "keywords": json.loads(r["keywords_json"] or "[]"),
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }

@router.patch("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    r = cur.fetchone()
    if not r:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    ts = now_iso()

    age = payload.age if payload.age is not None else r["age"]
    student = _bool_to_int(payload.student) if payload.student is not None else r["student"]
    region = payload.region if payload.region is not None else r["region"]
    category = payload.category_preference if payload.category_preference is not None else r["category_preference"]
    keywords_json = (
        json.dumps(payload.keywords, ensure_ascii=False)
        if payload.keywords is not None
        else r["keywords_json"]
    )

    cur.execute("""
        UPDATE users
        SET age=?, student=?, region=?, category_preference=?, keywords_json=?, updated_at=?
        WHERE id=?
    """, (age, student, region, category, keywords_json, ts, user_id))

    conn.commit()
    conn.close()

    return {"id": user_id, "updated_at": ts}