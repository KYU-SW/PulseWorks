# 근거 기반 임상보고서 Copilot을 적용한 웹 EMR 시스템

**Web-Based EMR with an Evidence-Grounded Clinical Report Copilot**

의료IT학과 학부 2학기 융합설계 기본(01분반)과목 프로토타입.

## 1. 프로젝트 소개

합성(가짜) EMR 데이터를 기반으로 로컬 LLM(또는 결정적 Mock)이 환자가 이해하기
쉬운 임상보고서 설명문 초안을 생성하고, 익명 근거 연결(Evidence Tag)과
결정적(deterministic) 검증, 의료진의 검토·수정·승인을 거쳐 **승인된 보고서만**
환자에게 제공하는 웹 기반 EMR 프로토타입이다.

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
환자 식별정보·내부 데이터베이스 식별자를 **LLM 입력 단계에서 제외·익명화**하고,
LLM 응답의 근거 태그·자기보고 수치·금지 표현을 서버가 결정적 규칙으로 점검하며,
최종적으로 의료진이 원본 근거를 확인·검토·승인한 내용만 환자에게 공개되는
구조를 설계·구현하는 것이 이번 과목 설계 프로토타입의 목적이다.

생성형 AI의 할루시네이션을 완전히 제거한다고 가정하지 않고, 입력 범위 제한,
생성 제약, 결정적 검증, 원본 근거 확인, 의료진 승인으로 위험을 다층 통제한다
(§8).

## 3. 시스템 전체 흐름

```
합성 EMR
  → 보고서 생성 시점의 임상정보를 EMR Snapshot으로 동결
  → 익명 Evidence Tag 생성(환자 식별정보·내부 ID 제외)
  → 로컬 LLM 또는 Mock이 설명문 초안 생성
  → 서버의 결정적 검증(근거 태그·자기보고 수치·금지 표현·태그 노출)
  → 의료진이 Evidence Viewer로 원본 근거 확인 후 검토·수정·저장
  → 의료진 승인(검토 확인 체크 필요) 또는 반려
  → 환자는 APPROVED 보고서만 조회
```

## 4. 사용자 역할

| 역할 | 현재 지원 상태 |
|---|---|
| DOCTOR(의사) | 담당 환자 조회, 보고서 생성·수정·승인·반려, 보고서 목록 — 구현됨 |
| PATIENT(환자) | 본인의 APPROVED 보고서만 조회 — 구현됨 |
| NURSE(간호사) | 로그인은 가능하나 전용 업무 화면은 아직 없음(준비 중 안내 화면으로 이동) |
| ADMIN_STAFF(행정직원) | 로그인은 가능하나 전용 업무 화면은 아직 없음 |
| SYSTEM_ADMIN(시스템 관리자) | 로그인은 가능하나 전용 업무 화면은 아직 없음 |

## 5. 현재 구현 기능 (웹 EMR)

**의료진(DOCTOR)**

- 담당 환자 목록과 담당 환자 검색(이름·MRN)
- 환자별 임상 타임라인과 진료(Encounter)별 요약 카드
- 진단·검사결과·검사 추세·활력징후·처방·알레르기 기록 조회
- 진료 단위 ClinicalReport(DRAFT) 생성, 설명문 초안 생성(Mock/LLM), 수정·저장
- 검사결과 상태 배지(HIGH/LOW/NORMAL/UNKNOWN)와 "참고범위 밖만 보기" 필터
  (보고서 화면)
- Evidence Viewer: 보고서에 동결된 EMR Snapshot의 활력징후·검사·진단을 원본
  근거로 확인
- 승인 전 검토 확인 체크(Approval Checklist), 보고서 승인·반려
- 진료 보고서 목록(`/doctor/reports`): 상태·작성일 기간 필터, 페이지네이션
- 타임라인의 보고서 생성·수정·승인·반려 이벤트 표시

**환자(PATIENT)**

- 본인의 APPROVED 보고서 목록
- 보고서 상세(설명문, 검사결과, 활력징후, 처방, 알레르기, 환자용 근거 요약)

**공통**

- JWT 기반 역할별 로그인
- 담당 관계(PatientAssignment) 기반 접근 제어
- 승인된 보고서의 수정·재승인 차단
- 주요 작업 감사 로그(AuditLog) 기록(조회 화면은 없음, §13)

NURSE·ADMIN_STAFF·SYSTEM_ADMIN 역할은 로그인 자체는 지원하지만, 각 역할에
맞는 전용 업무 화면은 **아직 구현되지 않았다**(§22 Known Limitations 참고).

## 6. Narrative Provider (Mock / 로컬 LLM)

설명문 생성은 두 Provider 중 하나로 동작한다(`backend/.env`의
`NARRATIVE_PROVIDER`로 전환). **기본값은 `mock`이다.**

| 모드 | 설명 |
|---|---|
| `mock` (기본값) | Deterministic Mock Provider. AI 모델·외부 호출 없이 EMR Snapshot에서 고정된 규칙으로 설명문을 만든다. 같은 입력이면 항상 같은 결과가 나오므로 재현 가능한 시연과 테스트에 사용한다. |
| `llm` | 로컬 Ollama의 `qwen3:8b` 계열 모델을 호출한다. Ollama 실행과 모델 설치가 별도로 필요하다(§19). |

- `llm` 모드에서 `LLM_VENDOR`/`LLM_BASE_URL`/`LLM_MODEL` 설정이 비어 있거나
  지원하지 않는 값이면 **Mock으로 조용히 대체하지 않고** 설정 오류(HTTP 503)로
  처리한다.
- LLM 호출은 `LLM_TIMEOUT_SECONDS`(기본 30초) 단위로 최대 2회 시도한다.
- 어느 Provider를 쓰든 응답은 동일한 구조화 출력(`LlmStructuredOutput`) 형식을
  따르며, 서버의 결정적 검증(§8.1)을 거친다.

## 7. Evidence Tag 구조

| 태그 | 의미 |
|---|---|
| `E` | Encounter(진료 방문) |
| `D` | Diagnosis(진단) |
| `L` | LabResult(검사결과) |
| `P` | Prescription(처방) |
| `A` | Allergy(알레르기) |
| `V` | VitalSign(활력징후) |

처리 원칙:

- 실제 `source_record_ids`(내부 숫자 PK 기반 식별자)는 LLM에 전송하지 않는다.
- 서버가 이번 요청에 한해 실제 기록을 `E1`, `D1`, `L1`, `V1` 같은 익명 태그로
  변환해 LLM에 전달하고, 태그→실제 기록 매핑은 서버에만 둔다.
- LLM은 narrative 작성에 실제로 사용한 익명 태그만 `evidence_tags` 필드로
  반환한다(모든 태그 유형을 강제로 쓰게 하지 않는다).
- Evidence Tag 문자열이 narrative 본문에 그대로 나타나면 검증에서 거부되며,
  환자 화면에도 노출되지 않는다.

## 8. AI 안전 통제 (Hallucination 위험 다층 통제)

이 프로젝트는 생성형 AI의 할루시네이션을 **완전히 제거한다고 주장하지 않는다.**
대신 다음 단계를 겹쳐 위험을 줄이고, 최종 판단은 의료진에게 둔다.

1. **입력 범위 제한**: 보고서 생성 시점의 구조화된 EMR Snapshot만 LLM 입력으로
   쓴다. 환자 이름·MRN·생년월일, 임상 메모, 내부 DB ID는 입력에서 제외되고
   익명 Evidence Tag로 대체된다.
2. **생성 제약(Prompt)**: 자료에 없는 사실·수치·근거 생성, 새 진단, 악화/호전
   판단, 치료·약물 변경 권고, 예후 판단, 검사와 진단 사이의 임의 인과관계 서술을
   금지한다. 검사 수치를 언급하면 구조화 필드(`mentioned_measurements`)에 함께
   보고하도록 요구한다.
3. **LLM narrative 생성**: 구조화 출력(JSON Schema) 형식으로만 받는다.
4. **결정적 Narrative Validator**: 아래 §8.1의 규칙을 서버가 결정적으로
   점검하고, 실패하면 아무것도 저장하지 않는다.
5. **Evidence Viewer**: 의료진이 보고서에 동결된 EMR Snapshot(활력징후·검사·
   진단)을 원본 근거로 직접 확인한다.
6. **의료진 편집·검토**: DRAFT 설명문을 의료진이 수정·저장할 수 있고, 서버가
   출처(`narrative_source`)와 의료진 수정 여부(`narrative_edited_by_clinician`)를
   기록한다.
7. **Approval Checklist**: "보고서 내용과 근거 데이터를 직접 확인했습니다"를
   체크해야 최종 승인 버튼이 활성화된다(현재 Frontend 자기확인 방식, §22).
8. **APPROVED-only 공개**: 의료진이 승인한 보고서만 환자에게 공개된다(§10).
9. **CDA Structured Entry 분리**: CDA XML의 구조화 entry는 LLM 출력이나 LLM의
   자기보고(`evidence_tags`, `mentioned_*`)가 아니라, Backend가 구조화된
   Snapshot에서 결정적으로 생성한다(§12).

### 8.1 결정적 검증이 실제로 하는 것

LLM 응답(`llm` 모드)에 대해 서버는 저장 전에 다음을 점검한다.

- 입력에 없는(허용되지 않은) Evidence Tag가 하나라도 있으면 전체 거부
- 빈 `evidence_tags`, 빈 narrative, 길이 상한 초과 거부
- 인용된 근거가 해당 보고서 Snapshot에 실제로 존재하는지 확인
- LLM이 `mentioned_measurements`로 **자기보고한** 검사 수치·단위·검사명이
  Snapshot의 실제 LabResult와 정확히 일치하는지 대조(활력징후도 동일)
- 지정된 금지 표현(문자열 일치) 포함 시 거부
- Evidence Tag 문자열(`[E1]`, `(D1)`, `{L1}` 등)이 narrative 본문에 노출되면
  거부
- 검증 실패 시 `ClinicalReport`와 `AiSummary` 어느 쪽에도 저장하지 않는다
  (부분 저장 없음, 일반화된 오류 메시지 반환)

Mock 응답은 비어 있지 않은지와 인용 근거가 Snapshot에 속하는지만 점검한다
(Mock은 Snapshot에서 규칙적으로 생성되기 때문).

### 8.2 결정적 검증의 한계

- narrative **본문 전체에서 숫자를 다시 추출해 검증하지 않는다.** LLM이
  자기보고하지 않은 수치는 대조 대상이 아니다.
- 금지 표현은 지정된 문자열 일치로만 검사하므로, 다르게 바꿔 쓴 표현은 놓칠 수
  있다.
- 의료적 적절성이나 임상적 안전성을 판단·보증하지 않는다.
- 따라서 Validator는 위험을 줄이는 한 단계일 뿐이며, 최종 확인은 의료진의
  근거 확인·검토·승인에 의존한다.

### 8.3 개인정보 입력 경계

개인정보 보호의 핵심은 "Validator가 모든 개인정보를 사후에 탐지한다"가 아니라
**"AI 입력 Snapshot을 구성하는 단계에서 불필요한 환자 식별정보와 내부 ID를
제외·익명화한다"**이다.

- 환자 이름·MRN·생년월일과 내부 DB ID는 LLM prompt에 포함되지 않는다.
- 현재 Validator에는 환자 식별정보·진단 코드·`rule_id` 패턴을 사후 탐지하는
  규칙이 없다. 이들은 애초에 LLM 입력에 들어가지 않는 방식으로 통제된다.

## 9. 보고서 상태 전이와 의료진 Human-in-the-Loop

```
DRAFT ──승인──▶ APPROVED   (수정·재승인 불가)
DRAFT ──반려──▶ REJECTED
REJECTED ──의료진 수정·저장──▶ DRAFT ──▶ 다시 승인 또는 반려
```

- 승인·반려는 DRAFT 보고서에만 할 수 있다(그 외 상태는 409).
- 반려하면 **REJECTED 상태로 남는다.** 의료진이 내용을 수정·저장하면 그때
  DRAFT로 돌아간다. 반려 사유 입력·저장 기능은 없다.
- `DOCTOR_REFERENCE` 유형 보고서(시연에서 생성하는 기본 유형)는 설명문이
  비어 있으면 승인할 수 없다.
- APPROVED 보고서는 수정할 수 없다(409).
- 생성·조회·설명문 생성·수정·승인·반려는 AuditLog에 기록된다.

## 10. 환자 APPROVED-only 공개

상태별 환자 공개 정책(Backend에서 강제):

| 상태 | 환자 공개 여부 |
|---|---|
| DRAFT | 공개 안 됨 |
| REJECTED | 공개 안 됨 |
| APPROVED | 공개됨 |

- 환자 목록 API는 APPROVED만 조회하고, DRAFT/REJECTED 보고서를 직접 요청하면
  존재하지 않는 보고서와 같은 404를 반환한다.
- 환자용 API 응답은 허용 필드 목록(allow-list) 방식으로 구성되며, 다음은
  환자 화면과 환자용 API 응답에 포함되지 않는다:
  - Evidence Tag
  - `source_record_ids`, `emr_snapshot` 원본
  - `narrative_source`, `narrative_edited_by_clinician`
  - Provider / Vendor / Model 이름
  - 개별 임상기록의 내부 DB ID(보고서 자체 ID는 조회 경로에 사용됨)
  - 진단 코드, `rule_id`
  - `handoff_note`(의료진 간 인수인계 메모)
- 환자 화면에는 수정·승인 등 의료진용 컨트롤이 없다.

## 11. 검사결과 판정 기준 (LOW / NORMAL / HIGH / UNKNOWN)

```
LabResult.value + 저장된 reference_low / reference_high
        ↓
Backend의 결정적 비교(값 < 하한 → LOW, 값 > 상한 → HIGH, 경계 포함 범위 내 → NORMAL,
범위·값이 없거나 유효하지 않으면 UNKNOWN)
        ↓
보고서 생성 시 Snapshot에 고정
        ↓
Frontend StatusBadge(표시만 하며 재계산하지 않음)
```

본 프로토타입은 각 검사결과에 저장된 참고범위를 기준으로
LOW/NORMAL/HIGH/UNKNOWN을 구조적으로 판정한다. 합성 데이터의 참고범위
(예: HbA1c 4.0–6.0 %)는 시연용이며, 실제 의료기관 적용 시 해당 검사실·검사법·
대상군에 대해 검증된 참고범위를 연동해야 한다. 단위 변환은 하지 않는다.

## 12. HL7 CDA 적용 범위

HL7 CDA R2.0 Core를 기준으로 결정적 XML 생성 파이프라인을 구현했으며, 현재
XML well-formedness와 결정성(byte determinism)을 검증한다. 공식 XSD 기반
적합성 검증은 HL7 XSD 라이선스/재배포 조건 확인 후의 후속 범위로 둔다.

코드 위치: `backend/app/services/cda/` (Backend 내부 서비스 계층, 현재 API로
노출되지 않음)

**구현된 범위**

- 승인된 보고서 Snapshot → 입력 DTO → 중간 표현(IR) → XML의 결정적
  adapter / mapper / exporter
- `urn:hl7-org:v3` namespace, 공식 `ClinicalDocument.typeId`
  (`2.16.840.1.113883.1.3` / `POCD_HD000040`)
- ClinicalDocument Header subset(id, code, title, effectiveTime,
  confidentialityCode, languageCode)
- recordTarget/PatientRole, Author, Custodian, componentOf/EncompassingEncounter
- StructuredBody, Section, Observation, 혈압 Organizer(수축기/이완기)
- Section text(NarrativeBlock)
- HL7 V3 ActStatus `completed`
- 활력징후 LOINC 코드 선택, UCUM 단위 정규화(일부 단위 whitelist)
- CDA 설정값 검증과 Backend 시작 시 fail-fast
- XML well-formedness 테스트, 같은 입력에 대한 byte determinism 테스트

**부분 구현**

- V3 Data Types는 필요한 일부(II, CD/CE, PQ, TS, IVL)만 사용한다.
- 검사·진단의 표준 코드 연결은 하지 않고 `nullFlavor`로 표시한다. Section
  code·templateId는 출력하지 않는다.

특정 C-CDA 또는 국가(KR) CDA Implementation Guide 준수를 주장하지 않는다.

### 12.1 CDA 미완료 범위

- 공식 CDA R2.0 XSD 기반 schema validation
- 특정 Implementation Guide(C-CDA, 국가 IG, Schematron) 검증
- CDA export API
- CDA XML 다운로드 UI
- CDA export 감사(Audit) 이벤트

공식 normative XSD를 이 저장소에 포함(vendoring)·재배포할 수 있는 조건을 명확히
확인하지 못했기 때문에 XSD 파일을 포함하지 않았고, 따라서 XSD 기반 검증도
수행하지 않는다. 현재 CDA 출력은 공식 XSD 검증을 통과했다고 확인되지 않았다.

## 13. 보안·개인정보

| 항목 | 현재 상태 |
|---|---|
| 인증 | JWT(Bearer) 로그인 |
| 역할 기반 접근 | 모든 임상 API에서 Backend가 역할 검사 |
| 담당 관계 접근 제어 | PatientAssignment 기반. 미담당 환자는 존재하지 않는 것과 같은 404 |
| 환자 공개 범위 | APPROVED 보고서만, 허용 필드 목록 방식 응답 |
| 의사 보고서 목록 | 담당 환자 보고서만 DB 쿼리 단계에서 필터링, 목록에는 본문·설명문·Snapshot 미포함 |
| 근거 표시 | Evidence Viewer는 내부 ID 대신 사람이 읽을 수 있는 근거를 표시 |
| 설명문 검증 | 결정적 Narrative Validator(§8.1) |
| 감사 로그 | 로그인 성공, 담당 환자·타임라인·검사 추세 조회, 보고서 생성·조회·설명문 생성·수정·승인·반려, 처방·안전경고 생성을 AuditLog에 기록 |

현재 범위의 한계:

- AuditLog를 조회하는 화면(Audit Activity Viewer)은 없다.
- 로그인 실패는 감사 로그에 기록하지 않는다.
- `source_record_ids`는 의료진 UI와 환자 API·화면에 노출되지 않지만,
  의사용 보고서 API의 JSON 응답(Snapshot)에는 포함되어 있다.

데이터·저장소 원칙:

- 모든 의료정보는 합성(가짜) 데이터다. `Patient.mrn`은 전부 `SYN-` 접두사를,
  계정은 전부 `@example.test` 도메인을 쓴다.
- 실제 `backend/.env`, Ollama 모델 파일, Docker 볼륨은 Git에 포함하지 않는다.
- 실제 의료환경에 적용하기 전에는 별도의 보안 검토가 반드시 필요하다.

## 14. 기술 스택

실제 `requirements.txt`/`package.json`을 확인해 현재 사용 중인 것만 기재한다.

**Frontend**
- React 18
- TypeScript
- Vite

**Backend**
- FastAPI
- Python 3.11
- Pydantic (`pydantic-settings` 포함)
- SQLAlchemy
- Alembic
- lxml (CDA XML 직렬화)

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

## 15. 프로젝트 디렉터리 구조

```
EMR-System/
├─ backend/
│  ├─ app/
│  │  ├─ core/        # 설정, DB 세션, 인증 등 공통 기반
│  │  ├─ models/       # SQLAlchemy 모델
│  │  ├─ routers/      # FastAPI 라우터(API 엔드포인트)
│  │  ├─ schemas/      # Pydantic 스키마
│  │  ├─ services/     # Narrative Provider, 검증, CDA(services/cda) 등 도메인 서비스
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
│  │  └─ routes/       # 라우팅 가드
│  └─ .env.example
├─ docs/                # 설계 문서(과목 제출용)
├─ docker-compose.yml
└─ README.md
```

## 16. 실행 전 요구사항

- Docker Desktop(Windows, WSL2 백엔드) — PostgreSQL 컨테이너용
- Python 3.11 — Backend 가상환경용
- Node.js 18 이상, npm
- (로컬 LLM 모드를 쓰려면) Windows 호스트에 설치된 Ollama와 `qwen3:8b` 모델

## 17. 환경변수 설정

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

**Backend를 호스트에서 직접 실행하는 경우(§18 기본 방식)**:
`backend/.env.example`의 `DATABASE_URL`은 Docker Compose 내부 호스트명(`db`)
기준이므로, 호스트에서 실행할 때는 `backend/.env`의 `DATABASE_URL` 호스트를
`localhost`로 바꾼다(포트 5432는 Compose가 호스트에 게시한다).

`frontend/.env`의 `VITE_API_BASE_URL`은 `http://localhost:8000`을 사용한다.

### Mock 모드(기본값)

```
NARRATIVE_PROVIDER=mock
```

### 로컬 LLM(Ollama) 모드

`.env.example`에는 `LLM_VENDOR`/`LLM_MODEL`이 비어 있으므로 직접 채운다.

```
NARRATIVE_PROVIDER=llm
LLM_VENDOR=ollama
LLM_MODEL=qwen3:8b
LLM_BASE_URL=http://localhost:11434
```

Ollama는 로컬에서 실행되므로 `LLM_API_KEY`가 필요하지 않다(비워둔다).

## 18. 로컬 실행 (시연 환경)

**Canonical 시연 주소**

| 대상 | 주소 |
|---|---|
| Frontend | `http://localhost:5173` |
| Backend | `http://localhost:8000` |
| Swagger / OpenAPI | `http://localhost:8000/docs` |

Backend CORS는 `http://localhost:5173`만 허용한다. 5173이 이미 사용 중이라 Vite가
다른 포트(예: 5174)로 뜨면 로그인 요청이 CORS로 거부되므로, 기존 Vite를 정리한
뒤 5173으로 실행한다.

아래는 Windows PowerShell, 저장소 루트(`C:\Projects\EMR-System`은 예시 경로)
기준이다.

**1) Docker Desktop 실행 후 PostgreSQL 시작**

```powershell
docker compose up -d db
docker compose ps
```

**2) Backend 가상환경 준비(최초 1회)**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

**3) DB 스키마와 합성 데이터 준비(최초 1회)**

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.seed_synthetic_data
```

시드 스크립트는 이미 있는 데이터를 다시 만들지 않는다(재실행해도 안전).

**4) Backend 실행**

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

상태 확인:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/health/db
```

**5) Frontend 실행**

```powershell
cd ..\frontend
npm install
npm run dev
```

**6) 브라우저에서 `http://localhost:5173` 접속**

**주의**: 프로젝트 루트에서 `npm run dev`를 실행하면 그 위치에
`package.json`이 없어 실패한다. 반드시 `frontend` 디렉터리에서 실행한다.

**대안: Backend도 Docker Compose로 실행**

```powershell
docker compose up -d db backend
```

이 경우 Compose가 컨테이너용 `DATABASE_URL`(`db` 호스트)과
`LLM_BASE_URL`(`http://host.docker.internal:11434`)을 덮어쓴다. 호스트에서
직접 실행한 Backend와 동시에 띄우면 8000 포트가 충돌하므로 둘 중 하나만
사용한다.

## 19. Ollama(로컬 LLM) 모드 실행

기본 시연은 Mock 모드(§6)로 충분하다. 실제 LLM으로 시연하려면:

1. Windows에서 Ollama 백그라운드 서버를 실행한다(Ollama를 설치하면 보통
   자동으로 백그라운드 서비스로 실행된다).
2. 모델을 설치한다.

   ```powershell
   ollama pull qwen3:8b
   ```

3. Ollama 서버 상태와 설치된 모델을 확인한다.

   ```powershell
   Invoke-RestMethod http://localhost:11434/api/version
   ollama list
   ```

4. `backend/.env`를 §17의 로컬 LLM 모드 값으로 설정한다.
5. Backend를 재시작해 변경된 환경변수를 반영한다.
   - 호스트 직접 실행: 실행 중인 uvicorn을 종료하고 §18의 4)를 다시 실행
   - Docker Compose 실행: `docker compose up -d --force-recreate backend`
6. 보고서 화면의 "설명문 초안 생성" 버튼을 누르면 실제 모델이 호출된다.

**주소 구분**: Compose로 띄운 backend 컨테이너에서 `localhost`는 컨테이너 자기
자신이므로 `http://host.docker.internal:11434`로 Windows 호스트의 Ollama에
접근한다(docker-compose.yml에서 설정). 호스트에서 직접 실행한 backend는
`http://localhost:11434`를 쓴다.

Ollama 서버가 실행 중이고 Provider가 `llm`이면 `ollama run` 같은 명령을 따로
실행하지 않아도 된다. 모델 파일 저장 경로는 각자 Ollama 기본 설정을 쓰면 된다.

## 20. 합성 데모 계정과 시연 절차

**합성 데모 전용 계정**

| 이메일 | 역할 |
|---|---|
| `endocrine.doctor@example.test` | DOCTOR (SYN-0001 환자의 담당 내분비내과 의사) |
| `patient1@example.test` | PATIENT (SYN-0001 본인) |

데모 비밀번호: `demo1234`

- 위 계정은 시드 스크립트(`backend/scripts/seed_synthetic_data.py`)가 만드는
  `@example.test` 기반 합성 데모 전용 계정이며, 실제 개인정보가 아니다.
- 로컬 개발·시연 전용이며, 운영 환경에서 재사용해서는 안 된다.
- 시드에는 이 밖에 정형외과·응급의학과 의사, 간호사, 행정직원, 시스템 관리자,
  두 번째 환자 계정도 있다.

**권장 시연 흐름**

1. `http://localhost:5173`에서 의사 계정으로 로그인한다.
2. 대시보드에서 담당 환자를 검색해 SYN-0001 상세로 이동한다.
3. 임상 타임라인과 진료별 요약 카드를 확인한다.
4. 진료 항목에서 보고서를 생성하거나, 상단 "진료 보고서" 메뉴에서 기존 DRAFT
   보고서를 연다.
5. "설명문 초안 생성"을 누르고 Mock/AI 출처 안내 문구를 확인한다.
6. 검사결과 배지와 "참고범위 밖만 보기" 필터, Evidence Viewer(근거 기록)를
   확인한다.
7. 설명문을 수정·저장한다.
8. 승인 → 검토 확인 체크 → 최종 승인한다.
9. "진료 보고서" 목록에서 상태·기간 필터와 타임라인의 보고서 이벤트를 확인한다.
10. 로그아웃 후 환자 계정으로 로그인해 APPROVED 보고서 목록과 상세를 연다.
11. 환자 화면에 Evidence Tag, 수정·승인 버튼, DRAFT/REJECTED 보고서가 보이지
    않는지 확인한다.

이미 승인된 진료에서 보고서 생성을 다시 누르면 새 DRAFT가 만들어진다. 기존
보고서는 "진료 보고서" 메뉴에서 연다.

## 21. 자동 테스트

**Backend**

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

대부분의 Backend 테스트는 격리된 in-memory SQLite로 실행된다. 단,
`tests/test_db_connection.py`는 `backend/.env`의 `DATABASE_URL`로 실제
PostgreSQL에 접속하므로 전체 실행 전에 `db` 컨테이너를 띄워 둔다.

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

### 최종화 검증 결과 (2026-11-16, commit `a20b7d1` 기준)

| 항목 | 결과 |
|---|---|
| Backend 전체 | 752 passed / 0 failed |
| Frontend 전체 | 52 test files, 489 passed / 0 failed |
| Frontend production build | PASS |
| PostgreSQL 연결 테스트 | PASS |
| CDA 관련 회귀 테스트 | 127 passed |

CDA 관련 127 passed는 매핑·직렬화·well-formedness·결정성 테스트 결과이며,
**공식 XSD 검증 통과를 의미하지 않는다**(§12.1).

## 22. Known Limitations

- 기본 Narrative Provider는 `mock`이다. 실제 LLM 시연에는 Ollama와 `qwen3:8b`
  환경이 별도로 필요하다.
- 검사결과 참고범위는 합성 시연 데이터 기준이다(§11).
- AI 할루시네이션의 완전한 제거를 보장하지 않는다. Validator는 자기보고 수치와
  지정 규칙만 점검한다(§8.2).
- 공식 CDA XSD 검증과 특정 국가/C-CDA Implementation Guide 준수는 확인되지
  않았다(§12.1).
- Approval Checklist는 현재 Frontend 자기확인 방식이며, Backend 승인 API가 체크
  여부를 따로 기록·강제하지 않는다.
- 문장 단위 근거 인용, AI 초안과 의료진 최종본의 비교 화면은 없다.
- 감사 로그 조회 화면(Audit Activity Viewer)은 없다.
- NURSE·ADMIN_STAFF·SYSTEM_ADMIN 전용 업무 화면, 승인된 보고서의 정정·버전
  관리, 반려 사유 저장은 구현되지 않았다.
- 로컬 모델의 응답 시간은 하드웨어 성능과 모델 로딩 상태에 따라 달라지며,
  Frontend의 요청 취소가 이미 시작된 Backend·Ollama 작업을 즉시 중단시키지
  못할 수 있다.
- 실제 의료 목적으로 사용할 수 없으며, 실제 의료환경 적용 전 법적·윤리적·보안
  검토가 필요하다.

개발자 참고:

- 진료 보고서 목록의 작성일 기간 필터는 UTC 날짜 경계를 사용한다.
- CDA Organizer `statusCode`의 속성 구성은 공식 XSD 검증 단계에서 재검토가
  필요하다.

## 23. 향후 개발 계획

아래는 **아직 구현되지 않은** 계획이며, §5의 "현재 구현 기능"과는 명확히
구분된다.

- 문장 단위 근거 인용과 AI 초안 대비 의료진 최종본 비교
- 승인된 보고서의 정정·버전 관리
- AI 실행 메타데이터(모델 정보) 표시와 감사 로그 조회 UI
- 공식 CDA XSD 검증(라이선스 확인 후), CDA export API·다운로드·감사 이벤트
- `qwen3:8b`와 `qwen3:14b`의 품질·속도 비교
- 읽기 전용 임상정보 조회 도구와 제한적 권한의 근거 검토 Agent
- FHIR 상호운용성 검토

위 "근거 검토 Agent"는 다음을 하지 않는다:

- 진단 확정
- 처방 추가·변경·중단
- 보고서 자동 승인
- 환자에게 직접 공개
- DB 임의 수정

## 24. 프로젝트 종료 방법

**Frontend·Backend 종료**: `npm run dev`, uvicorn을 실행한 터미널에서 각각
`Ctrl+C`.

**DB 종료**(데이터 유지):

```powershell
docker compose stop db
```

Backend도 Compose로 실행했다면 `docker compose down`으로 컨테이너를 정리할 수
있다(볼륨은 유지됨).

**경고**: 다음 명령은 DB 볼륨을 삭제하므로 사용하지 않는다.

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
