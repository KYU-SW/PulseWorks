# 근거 기반 임상보고서 Copilot을 적용한 웹 EMR 시스템

**Web-Based EMR with an Evidence-Grounded Clinical Report Copilot**

의료IT학과 학부 2학기 융합설계 기본(01분반)과목 프로토타입.

## 1. 프로젝트 소개

합성(가짜) EMR 데이터를 기반으로 로컬 LLM이 환자가 이해하기 쉬운 임상보고서
초안을 생성하고, 익명 근거 연결(Evidence Tag)과 결정적(deterministic)
검증, 의료진의 검토·수정·승인을 거쳐 **승인된 보고서만** 환자에게 제공하는
웹 기반 EMR 프로토타입이다.

이 프로젝트는 다음이 **아닙니다**:

- 질병 예측모델
- AI 진단 시스템
- 자동 처방 시스템
- 의료 챗봇
- 의료진 대체 시스템
- 실제 의료기관용 상용 서비스
- 의료적 정확성이 보장된 AI

## 2. 프로젝트 목적

의료진이 작성하던 환자 안내용 설명문 초안을 로컬 LLM이 보조하게 하면서도,
환자 식별정보·내부 데이터베이스 식별자가 LLM에 전달되지 않도록 익명화하고,
LLM이 실제로 존재하지 않는 근거를 지어내거나 환자 식별정보를 역으로
노출하지 않는지 서버가 결정적으로 검증하며, 최종적으로 의료진이 검토·승인한
내용만 환자에게 공개되는 구조를 설계·구현하는 것이 이번 과목 설계 프로토타입의
목적이다.

## 3. 시스템 전체 흐름

```
합성 EMR
  → 필요한 임상정보 선별
  → 익명 Evidence Tag 생성
  → 로컬 LLM 또는 Mock이 설명문 DRAFT 생성
  → 서버의 근거·수치·금지 표현 검증
  → 의료진 검토·수정·저장
  → 의료진 승인 또는 반려
  → 환자는 APPROVED 보고서만 조회
```

## 4. 사용자 역할

| 역할 | 현재 지원 상태 |
|---|---|
| DOCTOR(의사) | 담당 환자 조회, 보고서 생성·수정·승인·반려 — 구현됨 |
| PATIENT(환자) | 본인의 APPROVED 보고서만 조회 — 구현됨 |
| NURSE(간호사) | 로그인은 가능하나 전용 업무 화면은 아직 없음(준비 중 안내 화면으로 이동) |
| ADMIN_STAFF(행정직원) | 로그인은 가능하나 전용 업무 화면은 아직 없음 |
| SYSTEM_ADMIN(시스템 관리자) | 로그인은 가능하나 전용 업무 화면은 아직 없음 |

## 5. 현재 구현 기능 (웹 EMR)

- 역할 기반 로그인
- 의사의 담당 환자 접근 제어
- 환자별 임상 타임라인
- 진료기록
- 진단기록
- 검사결과
- 검사 추세
- 처방기록
- 알레르기기록
- ClinicalReport DRAFT 생성
- 의료진의 보고서 수정·저장
- 보고서 승인·반려
- 환자의 APPROVED 보고서 조회
- 승인된 보고서의 수정·재승인 차단
- 주요 작업 감사 로그

NURSE·ADMIN_STAFF·SYSTEM_ADMIN 역할은 로그인 자체는 지원하지만, 각 역할에
맞는 전용 업무 화면은 **아직 구현되지 않았다**(§18 현재 제한사항 참고).

## 6. 로컬 LLM과 Mock Provider

설명문 생성은 두 Provider 중 하나로 동작한다(`NARRATIVE_PROVIDER` 환경변수로
전환):

- **Deterministic Mock Provider**: 외부 호출 없이 고정된 규칙으로 설명문을
  생성한다. 테스트와 기본 개발 환경에서 사용한다.
- **Ollama qwen3:8b Provider**: 로컬에서 실행 중인 Ollama의 `qwen3:8b`
  모델을 호출해 설명문을 생성한다.

어느 Provider를 쓰든 응답은 동일한 `LlmStructuredOutput` JSON Schema(구조화
출력)를 따라야 하며, 서버가 동일한 검증 절차(§8)를 거친다.

## 7. Evidence Tag 구조

| 태그 | 의미 |
|---|---|
| `E` | Encounter(진료 방문) |
| `D` | Diagnosis(진단) |
| `L` | LabResult(검사결과) |
| `P` | Prescription(처방) |
| `A` | Allergy(알레르기) |

처리 원칙:

- 실제 `source_record_ids`(내부 숫자 PK 기반 식별자)는 LLM에 전송하지 않는다.
- 서버가 이번 요청에 한해 실제 기록을 `E1`, `D1`, `L1`, `P1`, `A1` 같은
  익명 태그로 변환해 LLM에 전달한다.
- LLM은 narrative 작성에 실제로 사용한 익명 태그만 `evidence_tags` 필드로
  반환한다(모든 태그 유형을 강제로 쓰게 하지 않는다).
- 서버 내부에서만 이 태그를 실제 임상기록으로 역매핑한다.
- Evidence Tag 문자열 자체는 narrative 본문과 환자 화면 어디에도 노출되지
  않는다.

## 8. 결정적 검증 (Deterministic Validation)

LLM(또는 Mock)의 응답은 저장되기 전에 다음을 서버가 결정적으로 검증한다.

- 허용되지 않은(또는 입력에 없는) Evidence Tag가 하나라도 있으면 전체 거부
- 빈 `evidence_tags` 거부
- narrative에 언급된 검사값·단위가 실제 LabResult와 정확히 일치하는지 대조
- Evidence Tag 문자열(`[E1]`, `(D1)`, `{L1}` 등)이 narrative 본문에 그대로
  노출되면 거부
- 내부 DB ID, 진단 코드, `rule_id`가 노출되는 패턴이면 거부
- 검증 실패 시 `ClinicalReport`와 `AiSummary` 어느 쪽에도 저장하지 않는다
  (부분 저장 없음)

## 9. 의료진 Human-in-the-Loop

- 생성된 DRAFT는 의료진이 검토·수정할 수 있다.
- narrative가 Mock/LLM 중 어느 출처에서 생성됐는지(`narrative_source`), 그리고
  의료진이 그 내용을 실제로 수정했는지(`narrative_edited_by_clinician`)를
  서버가 추적한다.
- 의료진이 승인해야만 환자에게 공개된다(§10). 반려하면 다시 DRAFT로 돌아간다.

## 10. 환자 APPROVED-only 공개

상태별 환자 공개 정책:

| 상태 | 환자 공개 여부 |
|---|---|
| DRAFT | 공개 안 됨 |
| REJECTED | 공개 안 됨 |
| APPROVED | 공개됨 |

환자 화면과 환자용 API 응답에는 다음이 노출되지 않는다:

- Evidence Tag
- `source_record_ids`
- `narrative_source`
- `narrative_edited_by_clinician`
- Provider / Vendor / Model 이름
- 내부 DB ID
- 진단 코드
- `rule_id`
- LLM thinking 내용
- `handoff_note`(의료진 간 인수인계 메모)

## 11. 기술 스택

실제 `requirements.txt`/`package.json`을 확인해 현재 사용 중인 것만 기재한다.

**Frontend**
- React 18
- TypeScript
- Vite

**Backend**
- FastAPI
- Python
- Pydantic (`pydantic-settings` 포함)
- SQLAlchemy
- Alembic

**Database**
- PostgreSQL 16

**Local AI**
- Ollama
- qwen3:8b

**Infrastructure**
- Docker Compose

**Testing**
- Pytest
- Vitest (+ Testing Library, jsdom)

## 12. 프로젝트 디렉터리 구조

```
EMR-System/
├─ backend/
│  ├─ app/
│  │  ├─ core/        # 설정, DB 세션, 인증 등 공통 기반
│  │  ├─ models/       # SQLAlchemy 모델
│  │  ├─ routers/      # FastAPI 라우터(API 엔드포인트)
│  │  ├─ schemas/      # Pydantic 스키마
│  │  ├─ services/     # Narrative Provider, 검증 등 도메인 서비스
│  │  └─ utils/
│  ├─ alembic/         # DB Migration
│  ├─ scripts/         # 합성 데이터 시드 스크립트
│  ├─ tests/           # Pytest
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  │  ├─ api/          # 백엔드 API 클라이언트
│  │  ├─ auth/         # 인증 컨텍스트
│  │  ├─ components/   # UI 컴포넌트
│  │  ├─ pages/        # 화면 단위 페이지
│  │  └─ routes/        # 라우팅 가드
│  └─ .env.example
├─ docs/                # 설계 문서(과목 제출용)
├─ docker-compose.yml
└─ README.md
```

## 13. 실행 전 요구사항

- Docker Desktop(Windows, WSL2 백엔드)
- Node.js 18 이상, npm
- (로컬 LLM 모드를 쓰려면) Windows 호스트에 설치된 Ollama와 `qwen3:8b` 모델

## 14. 환경변수 설정

실제 `.env` 파일은 Git에 포함되지 않는다. `backend/.env.example`과
`frontend/.env.example`을 복사해서 각자 로컬 `.env`를 만든다. 아래는 각
파일을 **어떻게 채울지에 대한 설명**이며, 실제 비밀값(`JWT_SECRET`, DB
비밀번호, 개인 토큰 등)은 이 문서에 기록하지 않는다.

```powershell
cd backend
Copy-Item .env.example .env

cd ..\frontend
Copy-Item .env.example .env
```

### Mock 모드(기본값)

```
NARRATIVE_PROVIDER=mock
```

### 로컬 LLM(Ollama) 모드

```
NARRATIVE_PROVIDER=llm
LLM_VENDOR=ollama
LLM_MODEL=qwen3:8b
```

Ollama는 로컬에서 실행되므로 `LLM_API_KEY`가 필요하지 않다(비워둔다).

## 15. Backend·DB 실행

아래는 Windows PowerShell 기준 예시다(`C:\Projects\EMR-System`은 예시
경로이며, 실제로는 이 저장소를 clone한 경로를 사용한다). 프로젝트 루트에서
실행하는 상대경로 명령도 함께 적는다.

**절대경로 예시**

```powershell
cd C:\Projects\EMR-System
docker compose up -d db backend
docker compose ps
```

**상대경로(저장소 루트에서 실행)**

```powershell
docker compose up -d db backend
docker compose ps
```

**Backend 상태 확인**

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/db
```

## 16. Frontend 실행

```powershell
cd C:\Projects\EMR-System\frontend
npm install
npm run dev
```

접속 주소: `http://localhost:5173`

**주의**: 프로젝트 루트(`C:\Projects\EMR-System`)에서 `npm run dev`를
실행하면 그 위치에 `package.json`이 없어 실패한다. 반드시 `frontend`
디렉터리로 이동한 뒤 실행해야 한다.

## 17. Mock 모드 실행

`backend/.env`의 `NARRATIVE_PROVIDER=mock` 상태(기본값)에서 §15~16대로
backend·frontend를 실행하면 된다. 별도 설정이 필요 없다.

## 18. Ollama 모드 실행

1. Windows에서 Ollama 백그라운드 서버를 실행한다(Ollama를 설치하면 보통
   자동으로 백그라운드 서비스로 실행된다).
2. 모델을 설치한다.

   ```powershell
   ollama pull qwen3:8b
   ```

3. Ollama 서버 상태를 확인한다.

   ```powershell
   Invoke-RestMethod http://localhost:11434/api/version
   ```

4. 설치된 모델을 확인한다.

   ```powershell
   ollama list
   ```

5. `backend/.env`에서 `NARRATIVE_PROVIDER=llm`로 설정한다
   (`LLM_VENDOR=ollama`, `LLM_MODEL=qwen3:8b`는 `.env.example` 기준값 그대로
   사용).
6. backend 컨테이너를 재생성해 변경된 환경변수를 반영한다.

   ```powershell
   docker compose up -d --force-recreate backend
   ```

7. 웹 화면의 "설명문 초안 생성" 버튼을 누르면 실제 `qwen3:8b` 모델이
   호출된다.

**주소 구분**: Docker Compose로 띄운 backend 컨테이너는 Docker Compose
설정을 통해 Windows 호스트에서 실행 중인 Ollama의 다음 주소로 접근한다.

```
http://host.docker.internal:11434
```

(컨테이너 내부에서 `localhost`는 컨테이너 자기 자신을 가리키므로, Ollama가
실행 중인 Windows 호스트를 가리키려면 `host.docker.internal`이 필요하다.)

Windows 호스트에서 backend를 Docker 없이 직접 실행하는 경우에는 다음
주소를 쓴다.

```
http://localhost:11434
```

Ollama 백그라운드 서버가 이미 실행 중이고 Provider가 `llm`로 설정되어
있으면, 별도로 `ollama run qwen3:8b` 같은 명령을 따로 실행하지 않아도 웹의
생성 버튼을 누르는 시점에 백엔드가 Ollama API를 호출한다.

Ollama 모델 파일이 저장되는 경로(`OLLAMA_MODELS` 등)는 사용자 환경마다
다르게 설정할 수 있으며, 이 프로젝트가 특정 경로를 요구하지 않는다 — 각자
Ollama 설치 환경의 기본 설정을 그대로 쓰면 된다.

## 19. 자동 테스트

**Backend**

```powershell
cd backend
pytest
```

Backend 테스트는 실제 PostgreSQL이 아니라 격리된 in-memory SQLite로
실행되므로, Docker로 `db` 컨테이너를 띄우지 않아도 실행할 수 있다.

**Frontend**

```powershell
cd frontend
npm test
```

(`package.json`의 `test` 스크립트는 `vitest run`을 실행한다.)

**Frontend 프로덕션 빌드 확인**

```powershell
cd frontend
npm run build
```

### 마지막 확인 기준점

- Backend: 492 passed
- Frontend: 392 passed
- Frontend production build: success

이 숫자는 이번 README 갱신 시점까지 반영된 기능을 기준으로 마지막으로
확인된 값이며, 이후 기능 추가나 테스트 변경으로 달라질 수 있다.

## 20. 역할별 시연 절차

1. 의사 계정으로 로그인한다.
2. 담당 환자 상세와 임상 타임라인을 확인한다.
3. 설명문이 비어 있는 DRAFT 보고서를 연다.
4. "설명문 초안 생성"을 클릭한다.
5. AI 또는 Mock 출처 안내 문구를 확인한다.
6. 의료진이 문장을 수정한다.
7. 저장한다.
8. 승인한다.
9. 의사 계정을 로그아웃한다.
10. 환자 계정으로 로그인한다.
11. 승인일이 가장 최근인 APPROVED 보고서를 연다.
12. 설명문·검사·처방·알레르기·근거 자료가 표시되는지 확인한다.
13. 내부 Evidence Tag, 수정·승인 버튼이 화면에 보이지 않는지 확인한다.

## 21. 개인정보·보안 원칙

- 모든 의료정보는 합성(가짜) 데이터다.
- `Patient.mrn`은 전부 `SYN-` 접두사를 쓴다.
- 계정은 전부 `@example.test` 도메인을 쓴다.
- 환자 이름·MRN·생년월일은 LLM prompt에서 제외된다.
- 내부 DB 식별자는 LLM에 전달되지 않고 익명 Evidence Tag로 대체된다.
- 실제 `backend/.env`는 Git에 포함하지 않는다.
- Ollama 모델 파일과 Docker 볼륨은 Git에 포함하지 않는다.
- 실제 의료환경에 적용하기 전에는 별도의 보안 검토가 반드시 필요하다.

## 22. 현재 제한사항

- 모든 임상정보는 합성 데이터다.
- 실제 의료 목적으로 사용할 수 없다.
- 진단·예측·처방 기능이 아니다.
- LLM(또는 Mock)의 결과는 항상 의료진의 검토·승인이 필요하다.
- 승인된 보고서의 정정·버전 관리는 아직 구현되지 않았다.
- NURSE·ADMIN_STAFF·SYSTEM_ADMIN의 역할 전용 업무 화면은 아직 구현되지
  않았다.
- 로컬 모델의 응답 시간은 하드웨어 성능과 모델 로딩 상태에 따라 달라진다.
- 프론트엔드의 요청 취소(timeout/페이지 이동)는 브라우저 쪽 대기만
  중단시킬 뿐, 이미 시작된 backend·Ollama 쪽 작업을 즉시 중단시키지
  못할 수 있다.
- 동시에 여러 생성 요청이 들어오는 경우에 대한 DB 수준의 멱등성 강화는
  후속 과제로 남아 있다.
- 실제 의료환경에 적용하기 전에는 법적·윤리적·보안 검토가 반드시 필요하다.

## 23. 향후 개발 계획

아래는 **아직 구현되지 않은** 계획이며, §5·§6의 "현재 구현 기능"과는
명확히 구분된다.

- 의료진 검토 패널
- 보고서 단위·문장별 근거 보기
- 처방·알레르기 등 검토가 필요한 항목 표시
- 승인된 보고서의 정정·버전 관리
- `qwen3:8b`와 `qwen3:14b`의 품질·속도 비교
- 실행 메타데이터와 감사 UI
- 읽기 전용 임상정보 조회 도구
- 제한적 권한의 근거 검토 Agent
- FHIR 상호운용성 검토

위 "근거 검토 Agent"는 다음을 하지 않는다:

- 진단 확정
- 처방 추가·변경·중단
- 보고서 자동 승인
- 환자에게 직접 공개
- DB 임의 수정

## 24. 프로젝트 종료 방법

**Frontend 종료**: `npm run dev`를 실행한 터미널에서 `Ctrl+C`.

**Backend·DB 종료**:

```powershell
cd C:\Projects\EMR-System
docker compose down
```

**경고**: 다음 명령은 DB 볼륨을 삭제할 수 있으므로 사용하지 않는다.

```powershell
docker compose down -v   # 사용하지 말 것 — 합성 데이터가 저장된 DB 볼륨이 삭제됨
```

## 25. 면책 및 주의사항

- 이 프로젝트는 학습·연구·시연 목적의 프로토타입이다.
- 실제 의료 목적으로 사용할 수 없다.
- 의료적 판단과 진료를 대체하지 않는다.
- LLM(또는 Mock)이 생성한 모든 내용은 의료진의 검토가 필요하다.
- 합성 데이터만 사용하며, 실제 환자정보를 다루지 않는다.

## 26. 라이선스 상태

이 저장소의 라이선스는 아직 지정되지 않았습니다.

## 합성 데모 계정

| 이메일 | 역할 |
|---|---|
| `endocrine.doctor@example.test` | DOCTOR (SYN-0001 환자의 담당 내분비내과 의사) |
| `patient1@example.test` | PATIENT (SYN-0001) |

데모 비밀번호: `demo1234`

- 위 계정은 모두 `@example.test` 기반 합성 계정이다.
- 실제 개인정보가 아니다.
- 로컬 개발·시연 전용이며, 운영 환경에서 재사용해서는 안 된다.
