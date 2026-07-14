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
    cols = [r[1] for r in cur.fetchall()]
    return column in cols


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # =========================================================
    # 1) scholarships 테이블 (legacy 유지)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            raw_json TEXT,
            source_uddi TEXT,
            fetched_at TEXT
        );
    """)

    needed_cols = {
        "policy_key": "TEXT",
        "source_uddi": "TEXT",
        "fetched_at": "TEXT",
    }
    for col, col_type in needed_cols.items():
        if not _column_exists(conn, "scholarships", col):
            cur.execute(f"ALTER TABLE scholarships ADD COLUMN {col} {col_type};")

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_scholarships_policy_key
        ON scholarships(policy_key);
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_status ON scholarships(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_name ON scholarships(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_type ON scholarships(type);")

    # =========================================================
    # 2) policies 테이블
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_key TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            provider TEXT,
            period TEXT,
            start_date TEXT,
            end_date TEXT,
            status TEXT,
            link TEXT,
            condition TEXT,
            benefit TEXT,
            source TEXT,
            source_id TEXT,
            fetched_at TEXT,
            source_meta TEXT,   -- 수집 소스별 구조화 메타 (JSON). KOSAF=NULL, 온통청년=JSON
            raw_json TEXT
        );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_category ON policies(category);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_status ON policies(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_name ON policies(name);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_provider ON policies(provider);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_policies_source ON policies(source);")

    # 기존 DB 마이그레이션: source_meta 컬럼 없으면 추가
    if not _column_exists(conn, "policies", "source_meta"):
        cur.execute("ALTER TABLE policies ADD COLUMN source_meta TEXT;")
        print("[db] policies.source_meta 컬럼 추가 완료 (마이그레이션)")

    # =========================================================
    # 3) users 테이블
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nickname TEXT,
            gender TEXT,
            birthdate TEXT,          -- YYYY-MM-DD (나이는 생년월일로 자동 계산)
            income_level INTEGER,    -- 소득분위 1~10
            region TEXT,
            school TEXT,             -- 대학생 | 대학원생 | 기타
            student INTEGER,         -- 0/1
            keywords_json TEXT,
            created_at TEXT,
            updated_at TEXT
        );
    """)

    # 기존 DB 마이그레이션: 컬럼 없으면 추가
    migration_cols = {
        "nickname": "TEXT",
        "gender": "TEXT",
        "birthdate": "TEXT",
        "income_level": "INTEGER",
        "school": "TEXT",
        "kakao_id": "TEXT",
        "finnut_id": "TEXT",
        "acorn_balance": "INTEGER DEFAULT 0",
    }
    for col, col_type in migration_cols.items():
        if not _column_exists(conn, "users", col):
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type};")
            print(f"[db] users.{col} 컬럼 추가 완료 (마이그레이션)")

    # category_preference 제거는 SQLite가 DROP COLUMN 미지원이라 그냥 둠
    cur.execute("CREATE INDEX IF NOT EXISTS ix_users_region ON users(region);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_users_school ON users(school);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_kakao_id ON users(kakao_id);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_finnut_id ON users(finnut_id);")

    # =========================================================
    # 5) friend_requests 테이블
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS friend_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',   -- pending | accepted | rejected
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_freq_receiver ON friend_requests(receiver_id, status);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_freq_sender ON friend_requests(sender_id, status);")
    # 같은 두 사람 사이에 pending 요청 중복 방지용 (재요청은 상태 바뀐 후에만)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_freq_pending_pair
        ON friend_requests(sender_id, receiver_id, status)
        WHERE status = 'pending';
    """)

    # =========================================================
    # 6) friendships 테이블 (수락 시 양방향 2행 insert)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(friend_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_friendship_pair ON friendships(user_id, friend_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_friendship_user ON friendships(user_id);")

    # =========================================================
    # 7) challenges 테이블
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,       -- 소비절약 | 저축 | 투자공부 | 생활
            description TEXT,
            period_days INTEGER NOT NULL DEFAULT 7,
            created_by INTEGER,           -- users.id, NULL이면 시스템 기본 챌린지
            created_at TEXT,
            FOREIGN KEY(created_by) REFERENCES users(id) ON DELETE SET NULL
        );
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS ix_challenges_category ON challenges(category);")

    # =========================================================
    # 8) challenge_participants 테이블 (참여 + 누적 점수)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS challenge_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT,
            acorn_score INTEGER NOT NULL DEFAULT 0,   -- 랭킹용 누적 도토리
            current_streak INTEGER NOT NULL DEFAULT 0,
            last_checkin_date TEXT,                    -- YYYY-MM-DD, 중복 인증 방지
            FOREIGN KEY(challenge_id) REFERENCES challenges(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_participant_pair ON challenge_participants(challenge_id, user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_participants_user ON challenge_participants(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_participants_ranking ON challenge_participants(challenge_id, acorn_score);")

    # =========================================================
    # 9) challenge_checkins 테이블 (일별 인증 기록)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS challenge_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            challenge_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            checkin_date TEXT NOT NULL,    -- YYYY-MM-DD
            created_at TEXT,
            FOREIGN KEY(challenge_id) REFERENCES challenges(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_checkin_day ON challenge_checkins(challenge_id, user_id, checkin_date);")

    # =========================================================
    # 4) policy_eligibility 테이블
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS policy_eligibility (
            policy_id INTEGER PRIMARY KEY,
            min_age INTEGER,
            max_age INTEGER,
            region TEXT,
            student_required INTEGER,
            income_type TEXT,
            income_max_percent INTEGER,
            income_max_quintile INTEGER,
            keywords_json TEXT,
            evidence_json TEXT,
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