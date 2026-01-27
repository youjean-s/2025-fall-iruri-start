import sqlite3
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from app.db import get_conn
from app.schemas import ScholarshipOut, ScholarshipDetailOut

router = APIRouter(prefix="/scholarships", tags=["scholarships"])


@router.get("", response_model=List[ScholarshipOut])
def list_scholarships(
    q: Optional[str] = Query(default=None, description="상품명/기관명 검색"),
    status: Optional[str] = Query(default=None, description="진행중|예정|마감|정보없음"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    conn = get_conn()
    cur = conn.cursor()

    where = []
    params = []

    if q:
        where.append("(name LIKE ? OR type LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like])

    if status:
        where.append("status = ?")
        params.append(status)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT id, policy_key, name, type, period, start_date, end_date, status, link,
               condition, grant, source_uddi, fetched_at
        FROM scholarships
        {where_sql}
        ORDER BY
            CASE status
                WHEN '진행중' THEN 1
                WHEN '예정' THEN 2
                WHEN '마감' THEN 3
                ELSE 4
            END,
            end_date DESC,
            id DESC
        LIMIT ? OFFSET ?;
    """
    params.extend([limit, offset])

    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]


@router.get("/{scholarship_id}", response_model=ScholarshipDetailOut)
def get_scholarship(scholarship_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, policy_key, name, type, period, start_date, end_date, status, link,
               condition, grant, raw_json, source_uddi, fetched_at
        FROM scholarships
        WHERE id = ?;
    """, (scholarship_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="not_found")

    return dict(row)
