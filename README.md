# EMR System (프로토타입)

의료IT학과 학부 3학년 2학기 설계 과목 프로토타입. 전체 설계는
[`docs/superpowers/specs/2026-09-13-emr-system-design.md`](docs/superpowers/specs/2026-09-13-emr-system-design.md),
이번 학기 구현 범위는 [`docs/implementation-plan.md`](docs/implementation-plan.md),
작업 단위 계획은 [`docs/superpowers/plans/2026-09-14-emr-prototype-implementation.md`](docs/superpowers/plans/2026-09-14-emr-prototype-implementation.md)를 참고한다.

## 개발 환경 설정

### 환경변수 (`backend/.env`)

`backend/.env`는 Git에서 제외되며(`.gitignore`), 각자 로컬에서
`backend/.env.example`을 복사해 만든다. `backend/.env.example`에는
실제 값이 아닌 데모용 예시만 들어 있다.

```
cp backend/.env.example backend/.env
```

### `DATABASE_URL` 정책 — 같은 변수, 두 개의 유효한 값

`DATABASE_URL`은 **누가 접속하느냐에 따라 가리키는 호스트가 다르다**:

- **Windows 호스트에서 직접 실행할 때(`pytest`, `uvicorn` 등)**: `backend/.env`는
  `localhost:5432`를 가리킨다. Docker Compose가 `db` 서비스의 5432 포트를
  호스트에 게시(`ports: "5432:5432"`)하므로, 호스트 프로세스 입장에서는
  `localhost`가 맞는 주소다.
- **Docker Compose로 띄운 `backend` 컨테이너 안에서 실행할 때**: 컨테이너
  입장에서 `localhost`는 자기 자신이지 `db` 컨테이너가 아니다. 그래서
  `docker-compose.yml`의 `backend` 서비스는 `environment:`로
  `DATABASE_URL`만 `db:5432`를 가리키도록 **재정의**한다 — `env_file`로
  읽어온 `backend/.env`의 다른 값(`JWT_SECRET` 등)은 그대로 유지된다.

즉 `backend/.env` 파일 자체는 한 종류(호스트 실행 기준: `localhost`)로만
유지하고, 컨테이너 실행 시 필요한 값만 compose 파일에서 오버라이드하는
방식이다. 지금 단계에서는 `.env.local`/`.env.compose`처럼 파일을 분리하지
않는다 — 오버라이드가 한 줄(`DATABASE_URL`)뿐이라 파일을 나누는 비용이
더 크다고 판단했다. 환경변수가 늘어나 오버라이드가 많아지면 그때 분리를
재검토한다.

### 컨테이너로 전체 스택 실행

```
docker compose up -d db backend
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

### 프론트엔드 환경변수와 CORS (개발 전용 설정)

프론트엔드는 API 주소를 코드에 하드코딩하지 않고 `VITE_API_BASE_URL`
환경변수(`frontend/.env`, `.env.example`에 예시 있음)로 읽는다. 브라우저는
항상 호스트에 게시된 `http://localhost:8000`을 쓰고, Docker Compose 내부
서비스 주소(`http://backend:8000`)는 브라우저 코드에서 절대 쓰지 않는다
(브라우저는 그 호스트명을 해석할 수 없다).

React 개발 서버(`http://localhost:5173`)와 FastAPI(`http://localhost:8000`)는
포트가 달라 서로 다른 origin이라, 브라우저가 `fetch` 전에 보내는 CORS
preflight를 FastAPI가 통과시켜줘야 한다. `backend/app/main.py`에 **개발
전용** `CORSMiddleware`를 추가했다:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

- `allow_origins`는 `["*"]`가 아니라 개발 서버 주소만 명시적으로 허용한다.
- `allow_credentials=False` — 인증은 쿠키가 아니라 `Authorization: Bearer`
  헤더로 하므로 자격증명 포함 요청이 필요 없다.
- **향후 배포 시**: 허용 Origin을 지금처럼 코드에 고정하지 말고 환경변수로
  관리해야 한다(예: `CORS_ALLOWED_ORIGINS`를 `Settings`에 추가해 배포 도메인
  목록을 주입). 지금은 로컬 개발용 단일 origin만 허용한다.

## 합성(가짜) 데이터 — 실제 환자정보 아님

`backend/scripts/seed_synthetic_data.py`가 만드는 User/Patient/임상 데이터는
**전부 100% 합성(가짜) 교육용 데이터**다. 실제 환자, 실제 의료진, 실제
의료기관의 정보를 담지 않으며, 여기 적힌 진단·검사·처방 수치를 실제 임상
판단 기준으로 사용해서는 안 된다.

- `Patient.mrn`은 전부 `SYN-` 접두사 (`SYN-0001` ~ `SYN-0010`)
- `User.email`은 전부 `@example.test` 도메인(IANA가 테스트용으로 예약한 TLD)
- `Patient`/`User.full_name`은 전부 "합성"이 포함된 placeholder 이름 (예: `합성환자-내분비01`)
- 진단·진료기록 등 임상 텍스트에는 필요한 경우 "(합성 데이터)" 표시를 붙임
- 주민등록번호 등 실제 개인식별번호 필드는 스키마에도, seed 데이터에도 없음

실행 방법 (idempotent — 여러 번 실행해도 중복 생성되지 않음):

```
cd backend
python -m scripts.seed_synthetic_data
```

### 로컬 데모 계정 (실제 운영 자격증명 아님)

Task 5부터 모든 합성 계정은 실제 bcrypt 해시로 로그인할 수 있다. 비밀번호는
전부 동일하게 `demo1234`이며(`scripts/seed_synthetic_data.py`의 `DEMO_PASSWORD`),
**로컬/CI의 합성 데이터베이스에서만 의미가 있는 교육용 비밀번호**다 — 실제 서비스
자격증명으로 오해하거나 재사용해서는 안 된다.

| 이메일 | 역할 |
|---|---|
| `endocrine.doctor@example.test` | DOCTOR (내분비내과) |
| `orthopedic.doctor@example.test` | DOCTOR (정형외과) |
| `emergency.doctor@example.test` | DOCTOR (응급의학과) |
| `nurse1@example.test` | NURSE |
| `admin.staff@example.test` | ADMIN_STAFF |
| `system.admin@example.test` | SYSTEM_ADMIN |
| `patient1@example.test` | PATIENT (내분비내과 핵심 환자) |
| `patient2@example.test` | PATIENT (정형외과 핵심 환자) |

```
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"endocrine.doctor@example.test","password":"demo1234"}'
```

기존에 Task 4의 placeholder 해시로 만들어진 계정이 있어도, seed 스크립트를 다시
실행하면 해당 계정만 실제 해시로 갱신되고 임상 데이터는 중복 생성되지 않는다.

## 안전 알림 기능의 한계 (Task 9, 10)

`evaluate_lab_abnormal()`(검사값 참고범위 비교, Task 9)과
`check_allergy_conflict()`(알레르기-처방 충돌 확인, Task 10)는 교육용 데모
규칙일 뿐이며 다음 한계가 있다.

- 교육용 합성 데이터만을 대상으로 하며, 실제 환자·의료기관 데이터를
  사용하지 않는다.
- `check_allergy_conflict()`는 등록된 합성 Allergy 이름과 입력된
  medication_name을 제한된 문자열 규칙(정규화 후 단어 경계 접두어 일치)으로
  비교할 뿐이다. 실제 성분·약물계열 데이터베이스를 사용하지 않으며,
  Amoxicillin과 Penicillin처럼 실제로는 같은 계열인 약물도 계열 관계를
  추론하지 않는다.
- 교차반응 판정, 약물상호작용 평가, 중증도 임상 평가, 처방 적절성 판단,
  대체 약물 추천을 수행하지 않는다.
- 이 알림들은 처방을 자동으로 차단·변경·취소하지 않는다 — 충돌이 있어도
  처방은 정상적으로 저장되며, 의료진의 확인을 요청하는 경고만 제공한다.
- 최종 판단과 처방 결정은 항상 의료진이 수행한다. 이 알림은 교육용
  합성 데이터를 제한된 문자열 규칙으로 비교한 데모 기능이며, 실제 처방
  안전성을 보장하지 않는다.
- 운영 환경에서는 검증된 의약품 코드체계(예: ATC), 실제 약물상호작용
  데이터베이스, DB 수준의 동시성 제약이 추가로 필요하다.

## 검사 추세 그래프의 한계 (Task 11)

`GET /patients/{patient_id}/lab-trends`와 프론트엔드 `LabTrendSection`도
같은 원칙을 따른다.

- 그래프와 표는 교육용 합성 데이터와 데모 참고범위만 사용한다.
- `evaluate_lab_abnormal()`(Task 9)의 기계적 판정을 그대로 보여줄 뿐,
  그래프 자체가 진단이나 예측을 수행하지 않으며 AI가 추세를 해석하지
  않는다.
- 측정값이 1건뿐인 검사는 추세로 표시하지 않고 단일 결과 카드로만
  보여준다.
- 그래프의 X축은 측정 시각을 균등한 간격으로 배치한 것으로, 실제 경과
  시간에 비례하지 않는다 — 이번 학기 데모 데이터(측정 건수가 적음)에는
  단순화된 표현으로 충분하다고 판단했다. 측정 건수가 늘어나면 시간
  비례 축으로 개선이 필요하다.
- 차트는 별도 라이브러리 없이 순수 SVG로 구현했다 — 판정 상태(LOW/
  NORMAL/HIGH/UNKNOWN)는 항상 색상과 텍스트로 함께 표시되며, 그래프
  아래 표에도 동일한 정보가 있어 색상을 구분하지 못해도 이해할 수
  있다.
