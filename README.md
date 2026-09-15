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
- `User.hashed_password`는 실제 비밀번호 해시가 아니라 인증에 쓰일 수 없는
  명백한 placeholder 문자열이다(`SEED_PLACEHOLDER_NOT_A_REAL_HASH__...`).
  실제 비밀번호 해시는 로그인 기능을 구현하는 후속 Task에서 처리한다.

실행 방법 (idempotent — 여러 번 실행해도 중복 생성되지 않음):

```
cd backend
python -m scripts.seed_synthetic_data
```
