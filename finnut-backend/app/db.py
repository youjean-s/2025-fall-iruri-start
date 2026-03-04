import os
import sqlite3
from datetime import datetime

# DB 경로 통일 (루트/data/kosaf_scholarships.db)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "kosaf_scholarships.db")


def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    cols = [r[1] for r in cur.fetchall()]  # (cid, name, type, notnull, dflt_value, pk)
    return column in cols


def init_db():
    """
    - 테이블 생성
    - 기존 테이블이 있으면 필요한 컬럼 추가(최소 마이그레이션)
    - scholarships: legacy 유지
    - policies: 통합 정책 테이블
    - users: 사용자 프로필
    - policy_eligibility: 정책 조건 구조화(추천/필터 1차 컷 용)
    """
    conn = get_conn()
    cur = conn.cursor()

    # =========================================================
    # 1) scholarships 테이블 (legacy 유지)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- 서비스용 핵심
            policy_key TEXT,
            name TEXT,
            type TEXT,
            period TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            link TEXT,
            condition TEXT,
            grant TEXT,

            -- 메타/원본
            raw_json TEXT,
            source_uddi TEXT,
            fetched_at TEXT
        );
    """)

    # 기존 scholarships 테이블에 컬럼 추가 (마이그레이션 안전장치)
    needed_cols = {
        "policy_key": "TEXT",
        "source_uddi": "TEXT",
        "fetched_at": "TEXT",
    }
    for col, col_type in needed_cols.items():
        if not _column_exists(conn, "scholarships", col):
            cur.execute(f"ALTER TABLE scholarships ADD COLUMN {col} {col_type};")

    # policy_key UNIQUE (upsert 기준)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_scholarships_policy_key
        ON scholarships(policy_key);
    """)

    # 보조 인덱스
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_status ON scholarships(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_name ON scholarships(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_type ON scholarships(type);")

    # =========================================================
    # 2) policies 테이블 (통합 정책 테이블)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- 통합 정책 공통 키
            policy_key TEXT UNIQUE,

            -- 서비스 공통
            name TEXT NOT NULL,
            category TEXT NOT NULL,          -- scholarship / housing / employment / subsidy ...
            provider TEXT,                   -- 기관/부처/운영기관
            period TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            link TEXT,
            condition TEXT,
            benefit TEXT,                    -- 지원내용

            -- 메타/원본
            source TEXT,                     -- odcloud-kosaf 등
            source_id TEXT,                  -- uddi 등
            fetched_at TEXT,
            raw_json TEXT
        );
    """)

    # policies 인덱스
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_category ON policies(category);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_status ON policies(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_name ON policies(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_provider ON policies(provider);")

    # =========================================================
    # 3) users 테이블 (사용자 프로필)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            age INTEGER,
            student INTEGER,            -- 0/1/NULL
            region TEXT,                -- "서울", "경기", "전국" 등
            category_preference TEXT,   -- scholarship/housing/employment/subsidy...
            keywords_json TEXT,         -- JSON list string
            created_at TEXT,
            updated_at TEXT
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_users_region ON users(region);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_users_category ON users(category_preference);")

    # =========================================================
    # 4) policy_eligibility (정책 조건 구조화)
    #    - policies.id와 1:1
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS policy_eligibility (
            policy_id INTEGER PRIMARY KEY,   -- policies.id (1:1)
            min_age INTEGER,
            max_age INTEGER,
            region TEXT,                     -- "전국"/"서울"/...
            student_required INTEGER,        -- 0/1/NULL

            income_type TEXT,                -- "median"/"quintile"/NULL
            income_max_percent INTEGER,      -- 예: 150 (중위소득 150%)
            income_max_quintile INTEGER,     -- 예: 8 (소득분위 8)

            keywords_json TEXT,              -- JSON list string (정책 태그)
            evidence_json TEXT,              -- JSON (근거 문장/출처)
            updated_at TEXT,

            FOREIGN KEY(policy_id) REFERENCES policies(id) ON DELETE CASCADE
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_elig_region ON policy_eligibility(region);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_elig_age ON policy_eligibility(min_age, max_age);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_elig_student ON policy_eligibility(student_required);")

    conn.commit()
    conn.close()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")