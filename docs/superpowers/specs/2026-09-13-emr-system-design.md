# EMR 프로토타입 설계 문서 (Design Spec)

- 작성일: 2026-09-13
- 상태: 확정 (사용자 승인 완료, 구현 착수 전)

## 0. 프로젝트 개요 및 범위

이 프로젝트는 의료IT학과 학부 **3학년 2학기 설계 과목**의 결과물이다. 단순한 병원 관리 웹사이트가 아니라 아래 의료정보학적 요소가 설계와 구현에 명확히 드러나야 한다:

1. Patient와 Encounter를 중심으로 임상 데이터를 구조화
2. 진단·검사·처방·알레르기·진료기록 간 관계를 명확히 설계
3. 내부 데이터와 FHIR 리소스 간 매핑 문서화
4. 사용자 직종·진료과·직급·담당 환자 관계에 따른 접근권한 결정
5. 최소권한 원칙과 감사 로그 적용
6. 환자 입력 자료와 의료기관 생성 자료 구분
7. AI 출력에 근거 원본 기록 ID 연결
8. 의료진 승인 전 AI 결과 환자 비공개
9. 안전 알림의 규칙·근거·우선순위 표시
10. 합성 환자자료만 사용 (실제 환자자료 금지)
11. 시스템은 진단·처방을 자동 결정하지 않음
12. 진료과별 화면은 코드 복제가 아닌 설정 기반으로 구성

전체 EMR 구조는 운영 확장을 고려하여 설계하되, **이번 학기에는 핵심 end-to-end 시나리오를 검증할 수 있는 교육용 프로토타입만 구현**한다. 이번 학기 구현 범위와 향후 확장 범위의 구분은 `docs/implementation-plan.md`에 별도 정리한다.

## 1. 아키텍처 & 기술 스택

- **모노레포** 구조: `backend/`(FastAPI + SQLAlchemy + Alembic), `frontend/`(React + TypeScript), `docs/`(필수 문서 10종 + 본 설계 문서), `scripts/`(합성 데이터 시더)
- DB: PostgreSQL
- 로컬 실행: `docker-compose`(postgres + backend + frontend) — 데모 재현성을 위해 단일 명령으로 구동
- 인증: 이메일/사번 + 비밀번호 로그인 → JWT 세션. 실 병원 SSO/EMR 계정 연동은 이번 학기 범위 밖(향후 확장 항목으로 문서화)
- 배포/스케일링은 다루지 않음(로컬 데모 재현만 보장)

## 2. 임상 데이터 모델 (요건 1, 2, 6)

Patient·Encounter를 중심으로 임상 데이터를 구조화한다.

- `Patient`: 합성 인구통계 정보
- `Encounter`: 방문/입원 단위, 진료과(department) FK 보유
- `Encounter`의 자식 엔티티: `Diagnosis`, `Order`(검사 처방), `LabResult`(검사결과), `Prescription`(처방), `ClinicalNote`(진료기록)
- `Allergy`: 특정 Encounter가 아니라 `Patient`에 직접 연결 (시점 무관하게 지속되는 정보)
- 모든 임상 레코드에 `source_type` 필드(`patient_reported` | `institution_generated`)를 두어 요건 6(환자 입력 자료 vs 의료기관 생성 자료 구분)을 데이터 레벨에서 강제
- 환자가 입력하는 자가측정값(예: 혈당 자가측정)은 `source_type=patient_reported`로 태깅되는 별도 관측 레코드로 취급 (FHIR 매핑상 `Observation`과 동일 리소스에 대응, 출처 플래그로 구분)
- 상세 ERD 및 필드 정의는 `docs/clinical-data-model.md` + `docs/erd.md`(또는 다이어그램)에 별도 작성·유지

## 3. 접근권한(RBAC) & 감사 로그 (요건 4, 5)

### 3.1 역할(Role) 정의

- `DOCTOR` (의사)
- `NURSE` (간호사)
- `ADMIN_STAFF` (원무과)
- `SYSTEM_ADMIN` (관리자)
- `PATIENT` (환자)

권한은 **직종 × 진료과 × 담당 환자 관계**의 조합으로 결정한다. 의료진 역할(DOCTOR/NURSE)은 소속 진료과와 담당 환자로 배정된 경우에만 상세 임상 기록에 접근 가능하다(예: 주치의, 담당 간호사).

### 3.2 PATIENT 역할 (환자)

환자는 다른 직종과 근본적으로 다른 규칙이 적용되며, 접근권한 매트릭스에 반드시 별도 행으로 포함한다.

- 자신의 기록만 조회할 수 있다. 다른 환자의 기록은 어떤 경우에도 조회할 수 없다 (직종/진료과 조건과 무관하게 최우선으로 적용되는 규칙).
- `APPROVED` 상태의 본인용 AI 요약만 볼 수 있다 (`DRAFT`/`REJECTED` 상태는 절대 비공개).
- 본인의 공개된 검사결과와 처방정보를 조회할 수 있다.
- 진료기록(ClinicalNote), 진단(Diagnosis), 처방(Prescription)은 직접 생성하거나 수정할 수 없다 (조회만 가능).
- 자가측정값(`source_type=patient_reported`인 Observation)은 입력할 수 있다.
- 본인 기록에 대한 접근 이력(감사 로그)을 확인할 수 있다 (본인 관련 항목으로 스코프된 조회).
- **이 제한은 프론트엔드뿐 아니라 백엔드 authorization 계층(중앙 authorization 서비스)에서 강제한다.** 라우터별 임시 체크가 아니라 공통 의존성을 통해 모든 리소스 접근 시 역할·소유권 검사를 거친다.

### 3.3 접근권한 매트릭스

`docs/access-control-matrix.md`에 아래 축으로 표를 작성한다:

- 행: `DOCTOR`, `NURSE`, `ADMIN_STAFF`, `SYSTEM_ADMIN`, `PATIENT`
- 열: 리소스(Patient 인적사항 / Encounter / Diagnosis / LabResult / Prescription / Allergy / ClinicalNote / AiSummary / AuditLog) × 액션(조회/생성/수정)
- 셀: 허용 여부 + 조건(예: "담당 환자인 경우만", "본인 데이터인 경우만")

### 3.4 감사 로그

- 모든 PHI 조회/생성/수정 행위를 `AuditLog`(append-only, 별도 삭제/수정 API 없음)에 기록: 행위자, 시각, 대상 리소스, 행위 종류, 적용된 권한 근거
- AI 요약의 생성·승인·반려도 감사 로그 대상 (섹션 4 참조)
- 감사 로그 정책은 `docs/audit-log-policy.md`에 별도 작성

## 4. AI 요약 승인 흐름 (요건 3, 7, 8)

- `AiSummary` 엔티티 상태는 이번 프로토타입에서 **`DRAFT` / `APPROVED` / `REJECTED`** 3가지로 확정한다.
  - `DRAFT`: 목업 요약 생성기가 만든 초기 상태 — 환자에게 절대 비공개
  - `APPROVED`: 의료진(DOCTOR)이 검토·승인 — **이번 프로토타입에서는 승인 상태를 환자 공개 상태와 동일하게 처리** (승인 즉시 환자 포털에 공개, 별도 `published` 상태 없음)
  - `REJECTED`: 의료진이 반려 — 환자에게 비공개, 필요 시 재생성 대상
- `source_record_ids` 필드에 근거가 된 ClinicalNote/LabResult 등 원본 레코드 ID를 배열로 저장 (요건 7)
- 요약 생성은 **목업(mock)** 처리: 실제 LLM API 연동 없이 규칙/템플릿 기반으로 encounter의 진단·검사값을 조립. 향후 실제 LLM API로 교체 가능하도록 생성 함수의 인터페이스는 분리해 둔다.
- AI 요약의 승인/반려는 **권한이 있는 의사(DOCTOR)만** 수행 가능
- 모든 생성·승인·반려 행위는 감사 로그에 기록
- **향후 운영 확장 시** 아래 상태 분리를 고려할 수 있음 (이번 프로토타입에는 미구현, 설계 문서에만 명시):
  - `APPROVED`: 의료진 승인 완료
  - `PUBLISHED`: 환자 공개 완료 (승인과 공개 시점을 분리)
  - `WITHDRAWN`: 공개 철회
- 승인 흐름도는 `docs/ai-summary-approval-flow.md`에 별도 작성

## 5. 환자 안전 알림 (요건 9, 11)

- 규칙 엔진 대상 (이번 프로토타입 범위):
  1. 알레르기-처방 충돌 체크 (환자 알레르기 목록 vs 처방 약물)
  2. 검사수치 이상범위 플래그 (LabResult가 참고범위를 벗어난 경우)
- `SafetyAlert` 레코드: `rule_id`(어떤 규칙이 발동했는지), `evidence`(충돌을 유발한 알레르기/검사값 레퍼런스), `priority`(예: high/medium/low)
- 안전 알림 규칙 명세는 `docs/patient-safety-alert-rules.md`에 별도 작성

### 5.1 안전성 원칙 (전체 시스템에 적용)

- AI는 진단하지 않는다.
- AI는 처방을 생성하거나 변경하지 않는다.
- 규칙 엔진은 검토 대상만 표시한다 (알림일 뿐, 결정이 아님).
- 시스템은 처방을 자동 확정하거나 대체하지 않는다.
- 최종 임상 판단과 처방 결정은 의료진이 수행한다.
- 모든 임상 데이터와 의약품 데이터는 합성 데이터만 사용한다.

## 6. 진료과별 설정 기반 화면 (요건 12)

데모 대상 진료과 3개:

- **내분비내과**: 이번 학기 핵심 시나리오의 주 무대 — 만성질환(당뇨) 추적 패널(HbA1c 추세 등)을 포함해 **주요 시나리오를 완전 구현**
- **정형외과**: 부위/영상 소개 중심 패널 — **설정 기반 화면과 주요 위젯 구현**
- **응급의학과**: 중증도 분류(triage)·활력징후·안전알림 우선순위 중심 패널 — **기본 화면만 구현**

React 쪽에는 진료과별 컴포넌트를 복제하지 않고, **스키마/설정 기반 공통 위젯 렌더러 하나**를 두고 진료과별 `department_config.json`(표시할 패널·위젯 목록)만 다르게 로드하여 화면을 구성한다. 이 구조 자체가 요건 12(코드 복제 금지)의 증거가 된다.

## 7. FHIR 매핑 (요건 3)

이번 학기에 아래 **6종 핵심 매핑**의 명세를 작성한다 (`docs/fhir-mapping-spec.md`):

| 내부 엔티티 | FHIR 리소스 |
|---|---|
| Patient | `Patient` |
| Encounter | `Encounter` |
| LabResult | `Observation` |
| Diagnosis | `Condition` |
| Allergy | `AllergyIntolerance` |
| Prescription | `MedicationRequest` |

- 시간이 허용되면 합성 환자 1명의 데이터를 위 6종 리소스로 구성된 **FHIR Bundle JSON**으로 내보내는 최소 프로토타입을 구현한다 (스트레치 목표, 필수 아님)
- `ClinicalNote`와 `AiSummary`의 `DocumentReference`/`Provenance` 매핑은 **설계 문서에는 포함하되 실제 구현은 방학 또는 4학년 확장 항목**으로 둔다

## 8. 핵심 시나리오 (이번 학기 acceptance 기준)

아래 end-to-end 시나리오가 동작하는 것을 이번 학기 구현의 완료 기준으로 삼는다:

1. 내분비내과 의사 로그인
2. 담당 환자 조회
3. 환자의 Encounter와 임상 타임라인 확인
4. HbA1c 검사 추세 확인
5. 검사 참고범위 이탈 플래그 확인
6. 데모 처방 입력 시 알레르기 충돌 알림 확인
7. Mock AI 요약 생성
8. 요약의 근거 record ID 확인
9. 의사의 AI 요약 승인
10. 환자 로그인
11. 승인된 요약 및 쉬운 설명 확인
12. 감사 로그 확인

이 시나리오는 자동화 테스트(pytest)와 수동 데모 스크립트 양쪽에서 커버하며, `docs/test-scenarios.md`에 테스트 케이스로 구체화한다.

## 9. 필수 문서 목록 및 소유 위치

구현과 함께 아래 문서를 반드시 작성·갱신한다 (각 문서는 관련 구현 변경 시 함께 갱신):

| 문서 | 경로 |
|---|---|
| 임상 데이터 모델 문서 | `docs/clinical-data-model.md` |
| ERD | `docs/erd.md` |
| 사용자별 접근권한 매트릭스 | `docs/access-control-matrix.md` |
| FHIR 매핑 명세 | `docs/fhir-mapping-spec.md` |
| 환자정보 데이터 흐름도 | `docs/patient-data-flow.md` |
| 감사 로그 정책 | `docs/audit-log-policy.md` |
| AI 요약 승인 흐름도 | `docs/ai-summary-approval-flow.md` |
| 환자 안전 알림 규칙 명세 | `docs/patient-safety-alert-rules.md` |
| 개인정보 및 보안 위협 모델 | `docs/security-threat-model.md` |
| 테스트 시나리오 | `docs/test-scenarios.md` |

## 10. 향후 확장 범위 (방학 / 4학년 프로젝트)

- `AiSummary` 상태를 `APPROVED`/`PUBLISHED`/`WITHDRAWN`으로 분리
- `ClinicalNote`/`AiSummary`의 `DocumentReference`/`Provenance` FHIR 매핑 실제 구현
- 실제 LLM API 연동으로 mock 요약 생성기 교체
- 3개 진료과 이상으로 설정 기반 화면 일반화
- 운영급 인증(SSO/병원 계정 연동), 배포, 감사 로그 저장소 확장성/보존정책
- FHIR Bundle 내보내기를 6종 이상(ClinicalNote/AiSummary 포함)으로 확장

## 부록: 이번 학기 구현 범위 구분

이번 학기 실제 구현 / 설계만 수행 / 향후 확장 항목의 구체적 분류는 `docs/implementation-plan.md`에 정리한다.
