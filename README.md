# Team 이루리 |대학(원)생의 생활비 부담 완화를 위한 소비습관 개선 및 장학•복지 정보 추천 어플리케이션: FINNUT

이 저장소는 이화여자대학교 졸업프로젝트 스타트 수업 (2025 Fall)을 위한
**팀 이루리(Iruri)**의 **초기 기획 및 핵심 기술 검증용** 레포지토리입니다.

FINNUT은 청년층의 지출/저축 패턴을 AI로 분석해, 맞춤 재정 관리 계획을 제안하고 올바른 금융 습관 형성을 돕는 청년 스마트 금융 케어 서비스입니다.

---

| 구분 | 내용 |
| --- | --- |
| **프로젝트명** | 대학(원)생의 생활비 부담 완화를 위한 소비습관 개선 및 장학•복지 정보 추천 어플리케이션: FINNUT|
| **주제** | 청년층의 재정적 불안정 해소 및 금융 습관 개선 |
| **핵심 목표** | 1) AI 기반 FHI 엔진을 통한 위험 소비 패턴 진단 및 코칭  2) API 및 웹 크롤링을 통한 흩어진 청년 복지/장학금 정보 자동 매칭 |
| **상태** | 핵심 로직 구현 및 기술 검증 완료 (Rule-based FHI + LightGBM 예측, 정책 데이터 수집/매칭) |

---

## ⚙️ 주요 기술 스택 및 활용

| 영역 | 주요 기술/패키지 | 활용 목적 |
| :--- | :--- | :--- |
| **Backend** | **FastAPI**, **uvicorn** | FHI 분석, 정책/장학금 매칭 API 서버 |
| **AI/ML** | **LightGBM** | FHI 하락 예측(7일 후 예상 FHI) 및 이상 소비 패턴 탐지를 위한 ML 모델 학습 |
| **코칭/NLG** | **ChatGPT API (gpt-4o-mini)** | FHI 진단 결과 기반, 사용자 맞춤형 코칭 카드 생성 |
| **데이터 처리** | **Python (pandas, re, datetime)** | 카드 알림 텍스트 파싱 및 FHI 지표 계산 |
| **정보 수집** | **공공데이터 API (한국장학재단, 온통청년)** & **웹 크롤러** | 장학금 및 청년 복지/금융사 혜택 정보 통합 확보 |
| **DB** | **SQLite** | 장학금/정책/사용자 데이터 저장 |
| **모바일 클라이언트** | **Kotlin / Jetpack Compose**, **Room DB** | 온디바이스 데이터 저장 및 UI |

---

## 🧑‍💻 Team 이루리 (역할 분담)

| 역할 | 담당 팀원 | 주요 기여 내용 |
| :--- | :--- | :--- |
| **PM & AI/Backend** | **송유진** | FHI 엔진(파싱, 충동/급증 지수) 및 LightGBM 예측 파이프라인 설계·구현, 프로젝트 총괄 |
| **Backend/DB** | **임슬민** | 한국장학재단 API 연동 및 데이터 수집 파이프라인(DB 적재) 구현 |
| **Frontend/Backend** | **정서진** | 복지/장학금 정책 매칭 로직 개발 및 Android 클라이언트 구성 |

---

## 📂 저장소 구조

| 폴더/파일 | 설명 |
| :--- | :--- |
| **app/** | FastAPI 백엔드 — 진입점(`main.py`), DB 초기화(`db.py`), 라우터(`routers/`: fhi, scholarships, policies, recommendations, users, eligibility) |
| **utils/** | FHI 엔진 핵심 로직 — 푸시 알림 파서, FHI 계산기, 충동소비 탐지기, 카테고리 분류 규칙 |
| **ml/** | LightGBM 학습/추론 파이프라인 — `src/`(학습·튜닝 스크립트), `ml_runtime/`(서비스용 feature builder·model loader), `artifacts/`(학습된 모델, 성능 리포트) |
| **scripts/** | 한국장학재단·온통청년 API 연동 및 DB 적재/마이그레이션 스크립트 |
| **mock/** | 푸시 알림 Mock 데이터 에뮬레이터 |
| **demo_pages/** | 정책 매칭, 푸시 파싱 등 핵심 기능 시연 및 테스트 스크립트 |
| **docs/** | 프로젝트 기획, 팀 규칙(`GroundRule.md`), 기술 문서 |
| **data/** | 장학금/정책 DB 파일(`kosaf_scholarships.db`) |
| **requirements.txt** | 프로젝트 환경 설정을 위한 필수 라이브러리 목록 |

---

## 🚀 설치 및 실행 방법

### 1. 저장소 클론

```bash
git clone https://github.com/youjean-s/2025-fall-iruri-start.git
cd 2025-fall-iruri-start
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

> Python 3.10 이상 권장

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 값을 채워주세요.

```env
OPENAI_API_KEY=발급받은_OpenAI_API_키
KOSAF_API_KEY=발급받은_한국장학재단_API_키
```

### 5. 백엔드 서버 실행

```bash
uvicorn app.main:app --reload
```

실행 후 `http://localhost:8000/health` 에서 정상 동작 여부를 확인할 수 있습니다.
DB(`data/kosaf_scholarships.db`)는 이미 저장소에 포함되어 있어 별도 초기화 없이 바로 사용 가능합니다.

### 6. FHI 예측 모델

학습된 LightGBM 모델은 `ml/artifacts/models/`에 포함되어 있어, 별도 재학습 없이 서버 실행 시 바로 추론에 사용됩니다. 모델을 다시 학습하고 싶다면 `ml/src/train_lgbm_baseline.py` 및 `ml/src/tune_lgbm_grid.py`를 참고하세요.

### 7. 핵심 로직 데모 / 테스트 실행

```bash
python demo_pages/check_week1_cases.py
python demo_pages/check_category_rules.py
python demo_pages/check_extremes.py
python demo_pages/check_rule_vs_ml.py
```

---

## 🔌 주요 API

| 분류 | 라우터 |
| :--- | :--- |
| 금융건강지수(FHI) | `app/routers/fhi.py` — 현재 FHI 진단, 7일 예상 FHI 예측 |
| 장학금/정책 매칭 | `app/routers/scholarships.py`, `policies.py`, `eligibility.py`, `recommendations.py`, `user_recommendations.py` |
| 사용자 | `app/routers/users.py` — Kakao 소셜 로그인, 프로필 등록 |

---

## 🤝 Ground Rule

팀 규칙은 **`docs/GroundRule.md`**에 정리되어 있습니다.