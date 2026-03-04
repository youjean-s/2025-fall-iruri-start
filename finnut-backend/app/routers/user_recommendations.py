import json
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Query, HTTPException
from app.db import get_conn

router = APIRouter(tags=["recommendations"])

ALLOWED_STATUS = {"진행중", "예정", "마감", "정보없음"}

def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _find_snippet(text: str, keyword: str, window: int) -> Optional[str]:
    if not text or not keyword:
        return None
    idx = text.find(keyword)
    if idx == -1:
        return None
    start = max(0, idx - window)
    end = min(len(text), idx + len(keyword) + window)
    snippet = text[start:end].replace("\n", " ").strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet

def _collect_snippets(policy: Dict[str, Any], keywords: List[str], window: int) -> List[Dict[str, str]]:
    name = _norm(policy.get("name"))
    provider = _norm(policy.get("provider"))
    condition = _norm(policy.get("condition"))
    benefit = _norm(policy.get("benefit"))

    sources: List[Tuple[str, str]] = [
        ("name", name),
        ("condition", condition),
        ("benefit", benefit),
        ("provider", provider),
    ]

    out: List[Dict[str, str]] = []
    for kw in keywords:
        k = _norm(kw)
        if not k:
            continue
        for source_name, text in sources:
            snip = _find_snippet(text, k, window)
            if snip:
                out.append({"keyword": k, "source": source_name, "snippet": snip})
                break
        if len(out) >= 6:
            break
    return out

def _score(policy: Dict[str, Any], user: Dict[str, Any], keywords: List[str]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []

    status = _norm(policy.get("status"))
    if status == "진행중":
        score += 30
        reasons.append("현재 신청 가능(진행중)")
    elif status == "예정":
        score += 10
        reasons.append("곧 신청 시작(예정)")
    elif status == "마감":
        score -= 50
        reasons.append("현재 마감")

    # 카테고리 선호
    cp = _norm(user.get("category_preference"))
    if cp and _norm(policy.get("category")) == cp:
        score += 40
        reasons.append(f"선호 카테고리 일치({cp})")

    # 키워드 매칭
    blob = " ".join([
        _norm(policy.get("name")),
        _norm(policy.get("provider")),
        _norm(policy.get("condition")),
        _norm(policy.get("benefit")),
    ])
    for k in keywords:
        k = _norm(k)
        if not k:
            continue
        if k in _norm(policy.get("name")):
            score += 10
            reasons.append(f"키워드 '{k}'가 정책명에 포함")
        elif k in blob:
            score += 5
            reasons.append(f"키워드 '{k}'가 조건/혜택/기관에 포함")

    return score, reasons[:6]

@router.get("/users/{user_id}/recommendations")
def recommend_for_user(
    user_id: int,
    top_n: int = Query(default=10, ge=1, le=50),
    exclude_closed: bool = True,
    include_snippets: bool = True,
    snippet_window: int = Query(default=40, ge=10, le=120),
    keyword: List[str] = Query(default_factory=list, description="추가 검색 키워드(여러 개 가능)"),
) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()

    # 1) 사용자 로드
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    u = cur.fetchone()
    if not u:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    user = {
        "id": u["id"],
        "age": u["age"],
        "student": (None if u["student"] is None else bool(u["student"])),
        "region": u["region"],
        "category_preference": u["category_preference"],
        "keywords": json.loads(u["keywords_json"] or "[]"),
    }

    # 키워드 합치기(사용자 저장 + 쿼리 추가)
    keywords = []
    for k in (user["keywords"] + keyword):
        k = _norm(k)
        if k and k not in keywords:
            keywords.append(k)

    # 학생/청년 키워드 보강(스니펫/스코어용)
    if user["student"] is True:
        for t in ["대학생", "재학생", "학부", "대학원", "학생"]:
            if t not in keywords:
                keywords.append(t)
    if user["age"] is not None and 19 <= user["age"] <= 34:
        for t in ["청년", "청년층"]:
            if t not in keywords:
                keywords.append(t)

    # 2) eligibility 기반 1차 필터(SQL)
    # - 정책에 eligibility가 없으면(LEFT JOIN NULL) 일단 후보에 포함
    where = []
    params: List[Any] = []

    if exclude_closed:
        where.append("(p.status IS NULL OR p.status != '마감')")

    # 지역: eligibility.region이 NULL이면 통과, '전국'이면 통과, user.region과 같으면 통과
    if user["region"]:
        where.append("(e.region IS NULL OR e.region='전국' OR e.region=? )")
        params.append(user["region"])

    # 나이: e.min_age/e.max_age가 NULL이면 통과, 범위 밖이면 제외
    if user["age"] is not None:
        where.append("(e.min_age IS NULL OR e.min_age <= ?)")
        where.append("(e.max_age IS NULL OR e.max_age >= ?)")
        params += [user["age"], user["age"]]

    # 학생: e.student_required가 NULL이면 통과, 1이면 user.student True일 때만 통과
    if user["student"] is not None:
        where.append("(e.student_required IS NULL OR e.student_required = ?)")
        params.append(1 if user["student"] else 0)

    # 카테고리 선호가 있으면 1차로 줄여도 됨(선택)
    if user["category_preference"]:
        where.append("(p.category = ?)")
        params.append(user["category_preference"])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    cur.execute(f"""
        SELECT
            p.id, p.policy_key, p.name, p.category, p.provider,
            p.period, p.start_date, p.end_date, p.status,
            p.link, p.condition, p.benefit,
            p.source, p.source_id, p.fetched_at
        FROM policies p
        LEFT JOIN policy_eligibility e ON e.policy_id = p.id
        {where_sql}
        ORDER BY
            CASE p.status
                WHEN '진행중' THEN 1
                WHEN '예정' THEN 2
                WHEN '마감' THEN 3
                ELSE 4
            END,
            p.start_date DESC,
            p.id DESC
        LIMIT 800
    """, params)

    rows = cur.fetchall()
    conn.close()

    # 3) 점수화 + 근거 생성
    items: List[Dict[str, Any]] = []
    for r in rows:
        p = {
            "id": r[0],
            "policy_key": r[1],
            "name": r[2],
            "category": r[3],
            "provider": r[4],
            "period": r[5],
            "start_date": r[6],
            "end_date": r[7],
            "status": r[8],
            "link": r[9],
            "condition": r[10],
            "benefit": r[11],
            "source": r[12],
            "source_id": r[13],
            "fetched_at": r[14],
        }

        sc, reasons = _score(p, user, keywords)
        p["score"] = sc
        p["reasons"] = reasons

        if include_snippets:
            p["snippets"] = _collect_snippets(p, keywords, snippet_window)
        else:
            p["snippets"] = []

        items.append(p)

    items.sort(key=lambda x: x["score"], reverse=True)
    top = [p for p in items if p["score"] > -20][:top_n]

    return {
        "user": user,
        "top_n": top_n,
        "returned": len(top),
        "exclude_closed": exclude_closed,
        "include_snippets": include_snippets,
        "items": top,
    }
    