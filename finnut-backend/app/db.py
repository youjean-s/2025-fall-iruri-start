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
    - 기존 테이블이 있으면 필요한 컬럼 추가 
    - UNIQUE 키를 (policy_key)로 강화 (신규 생성 기준)
      * 기존 DB가 이미 UNIQUE(name,type,link)로 만들어진 경우도 유지되도록,
        policy_key는 별도로 UNIQUE INDEX로 추가
    """
    conn = get_conn()
    cur = conn.cursor()

    # 1) 기본 테이블 생성(신규)
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

    # 2) 기존 테이블에 컬럼 추가 
    needed_cols = {
        "policy_key": "TEXT",
        "source_uddi": "TEXT",
        "fetched_at": "TEXT",
    }
    for col, col_type in needed_cols.items():
        if not _column_exists(conn, "scholarships", col):
            cur.execute(f"ALTER TABLE scholarships ADD COLUMN {col} {col_type};")

    # 3) UNIQUE INDEX 추가 (policy_key 우선)
    #    - 이미 존재하면 에러 나므로 IF NOT EXISTS 사용
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_scholarships_policy_key
        ON scholarships(policy_key);
    """)

    # 4) 보조 인덱스(조회 성능)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_status ON scholarships(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_name ON scholarships(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_type ON scholarships(type);")

    conn.commit()
    conn.close()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")
