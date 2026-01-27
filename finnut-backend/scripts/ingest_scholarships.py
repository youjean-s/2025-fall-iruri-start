import os
import json
import hashlib
import requests
import sqlite3

import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from dotenv import load_dotenv
from datetime import datetime

#requests 예외 메시지 안에 포함된 URL의 serviceKey 값을 마스킹
#예: serviceKey=ABCDEF... -> serviceKey=***MASKED***
from app.db import init_db, get_conn, now_iso
def mask_service_key_in_text(text: str) -> str:

    text = re.sub(r"(serviceKey=)[^&\s]+", r"\1***MASKED***", text)
    return text

# ============================
# 환경변수 로드
# ============================
load_dotenv()
SERVICE_KEY = os.getenv("SERVICE_KEY")
if not SERVICE_KEY:
    raise ValueError("ERROR: .env 파일에 SERVICE_KEY가 없습니다!")

# ============================
# 설정
# ============================
BASE_URL = "https://api.odcloud.kr/api/15028252/v1"

# 월별 UDDI 엔드포인트 목록 (사용자 제공 그대로)
KOSAF_UDDIS = [
    "uddi:f8c87706-5533-4021-8582-dc44a646f61e" #260109
    "uddi:ec86fced-7440-4c0e-8047-9f1ec27919d5", #251111
    "uddi:c40ccdc5-8f56-4f1c-8531-f0264213f98c", #251201
]

# ============================
# 날짜 파싱 함수
# ============================
def parse_date(date_str):
    if not date_str or date_str == "-":
        return None
    date_str = str(date_str).replace(".", "-").replace("/", "-").strip()
    parts = date_str.split("-")
    if len(parts) == 3:
        y, m, d = parts
        try:
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
        except Exception:
            return None
    return None


# ============================
# 기간 정규화 + 상태 판단
# ============================
def build_period_and_status(row):
    start_raw = row.get("모집시작일", "")
    end_raw = row.get("모집종료일", "")

    start = parse_date(start_raw)
    end = parse_date(end_raw)

    today = datetime.today().date()

    if start and end:
        s = datetime.strptime(start, "%Y-%m-%d").date()
        e = datetime.strptime(end, "%Y-%m-%d").date()
        if s <= today <= e:
            status = "진행중"
        elif today < s:
            status = "예정"
        else:
            status = "마감"
    else:
        status = "정보없음"

    return {
        "period": f"{start or start_raw} ~ {end or end_raw}",
        "start": start,
        "end": end,
        "status": status
    }


# ============================
# 신청 자격(조건) 생성
# ============================
def build_condition(row):
    fields = [
        ("신청대상", row.get("신청대상")),
        ("지원대상", row.get("지원대상")),
        ("성적기준", row.get("성적기준 상세내용")),
        ("소득기준", row.get("소득기준 상세내용")),
        ("특정자격", row.get("특정자격 상세내용")),
        ("지역거주", row.get("지역거주여부 상세내용")),
        ("자격제한", row.get("자격제한 상세내용")),
    ]

    lines = []
    for label, value in fields:
        if value and str(value).strip() and value != "-":
            lines.append(f"{label}: {str(value).strip()}")

    return "\n".join(dict.fromkeys(lines))


# ============================
# 지원내용(grant) 생성
# ============================
def build_grant(row):
    fields = [
        row.get("지원내역 상세내용"),
        row.get("지원내역"),
        row.get("지원금액"),
        row.get("장학금액"),
        row.get("급여"),
    ]

    for f in fields:
        if f and str(f).strip() and f != "-":
            return str(f).strip()

    return ""


# ============================
# policy_key 생성(중복 방지 강화)
# - 링크가 없거나 바뀌어도 중복 폭발 안 나도록
# - (상품명 + 운영기관명 + 모집시작/종료 + 홈페이지주소 일부)를 기반으로 해시
# ============================
def build_policy_key(row):
    name = (row.get("상품명") or "").strip()
    org = (row.get("운영기관명") or "").strip()
    start = parse_date(row.get("모집시작일"))
    end = parse_date(row.get("모집종료일"))
    link = (row.get("홈페이지 주소") or "").strip()

    basis = f"{name}|{org}|{start or ''}|{end or ''}|{link}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:32]


# ============================
# API 호출 (페이지네이션 대응)
# - ODcloud는 보통 totalCount/currentCount 제공
# - data가 비거나, currentCount/totalCount로 종료 판단
# ============================
def fetch_all_pages(uddi, per_page=1000):
    url = f"{BASE_URL}/{uddi}"
    page = 1
    all_rows = []

    while True:
        params = {"page": page, "perPage": per_page, "serviceKey": SERVICE_KEY}
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        payload = r.json()

        data = payload.get("data", []) or []
        all_rows.extend(data)

        total = payload.get("totalCount")
        current = payload.get("currentCount")

        if not data:
            break
        if total is not None and len(all_rows) >= int(total):
            break
        if current is not None and len(data) < int(current):
            # 일부 API에서 currentCount 의미가 다를 수 있어 보수적으로 처리
            pass
        if len(data) < per_page:
            break

        page += 1

    return all_rows


# ============================
# row -> 저장용 dict 변환
# ============================
def convert_rows(rows, source_uddi: str):
    out = []
    fetched_at = now_iso()

    for row in rows:
        period_data = build_period_and_status(row)

        out.append({
            "policy_key": build_policy_key(row),
            "name": row.get("상품명"),
            "type": row.get("운영기관명", ""),
            "period": period_data["period"],
            "start_date": period_data["start"],
            "end_date": period_data["end"],
            "status": period_data["status"],
            "link": row.get("홈페이지 주소", ""),
            "condition": build_condition(row),
            "grant": build_grant(row),
            "raw_json": json.dumps(row, ensure_ascii=False),
            "source_uddi": source_uddi,
            "fetched_at": fetched_at,
        })

    return out


# ============================
# DB 저장 (policy_key 기준 upsert)
# ============================
def save_to_db(items):
    conn = get_conn()
    cur = conn.cursor()

    for p in items:
        # policy_key가 UNIQUE라서 충돌 시 업데이트
        cur.execute("""
            INSERT INTO scholarships
            (policy_key, name, type, period, start_date, end_date, status, link,
             condition, grant, raw_json, source_uddi, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(policy_key)
            DO UPDATE SET
                name = excluded.name,
                type = excluded.type,
                period = excluded.period,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                status = excluded.status,
                link = excluded.link,
                condition = excluded.condition,
                grant = excluded.grant,
                raw_json = excluded.raw_json,
                source_uddi = excluded.source_uddi,
                fetched_at = excluded.fetched_at;
        """, (
            p["policy_key"],
            p["name"],
            p["type"],
            p["period"],
            p["start_date"],
            p["end_date"],
            p["status"],
            p["link"],
            p["condition"],
            p["grant"],
            p["raw_json"],
            p["source_uddi"],
            p["fetched_at"],
        ))

    conn.commit()
    conn.close()


def run():
    print("=== FINNUT 장학금 데이터 수집 시작 ===")
    init_db()

    total_fetched = 0
    total_upserted = 0

    for uddi in KOSAF_UDDIS:
        print(f"[UDDI] {uddi} 수집 중...")

        try:
            rows = fetch_all_pages(uddi, per_page=1000)
            print(f" → {len(rows)}건 수집")
            total_fetched += len(rows)

            items = convert_rows(rows, source_uddi=uddi)
            save_to_db(items)
            total_upserted += len(items)

        except Exception as e:
            msg = mask_service_key_in_text(str(e))
            print(f" !! 실패: {uddi} / {msg[:200]}")


    print(f"=== 완료! fetched={total_fetched}, upserted={total_upserted} ===")


if __name__ == "__main__":
    run()