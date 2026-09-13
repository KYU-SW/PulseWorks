# 이번 학기 구현 범위 (3학년 2학기 설계 과목)

설계 근거: [`docs/superpowers/specs/2026-09-13-emr-system-design.md`](superpowers/specs/2026-09-13-emr-system-design.md)

전체 EMR 구조는 운영 확장을 고려해 설계하되, 이번 학기에는 핵심 end-to-end 시나리오를 검증할 수 있는 교육용 프로토타입만 구현한다. 결과물을 아래 세 범주로 구분한다.

## A. 이번 학기 실제 구현

- **데이터 모델 & DB**: Patient, Encounter, Diagnosis, Order, LabResult, Prescription, ClinicalNote, Allergy, AiSummary, SafetyAlert, AuditLog, User(역할 포함) — PostgreSQL + SQLAlchemy + Alembic 마이그레이션
- **인증**: 이메일/사번 + 비밀번호 로그인, JWT 세션
- **RBAC & 감사 로그**: DOCTOR/NURSE/ADMIN_STAFF/SYSTEM_ADMIN/PATIENT 5개 역할, 담당 환자 관계 기반 접근 제어를 중앙 authorization 계층(FastAPI 공통 의존성)으로 강제. 모든 PHI 접근을 AuditLog에 기록. PATIENT 역할의 본인 데이터 한정 조회 및 자가측정값 입력을 백엔드에서 강제
- **AI 요약**: 목업(규칙/템플릿 기반) 요약 생성기, `source_record_ids` 근거 연결, `DRAFT`/`APPROVED`/`REJECTED` 상태 및 승인·반려 API(DOCTOR 전용), 승인=공개 처리
- **환자 안전 알림**: 알레르기-처방 충돌 규칙, 검사수치 이상범위 플래그 규칙, `SafetyAlert`(rule_id/evidence/priority) 생성 및 조회
- **진료과별 설정 기반 화면**:
  - 내분비내과: 핵심 시나리오 전체(진단/검사/처방/알림/AI요약/승인/환자열람) 완전 구현
  - 정형외과: 공통 위젯 렌더러 + `department_config.json` 기반 화면과 주요 위젯 구현 (부위/영상 소개 패널 등)
  - 응급의학과: triage·활력징후·안전알림 우선순위 중심의 기본 화면 구현
- **합성 데이터 시더**: 스크립트로 합성 환자·Encounter·검사값·알레르기 데이터 생성 (`scripts/`)
- **핵심 시나리오 자동화 테스트**: 설계 문서 8절의 12단계 시나리오를 커버하는 pytest 테스트 + 권한별 접근 거부 케이스
- **필수 문서 10종**: 아래 "이번 학기 실제 구현"에 해당하는 구현 내용을 반영해 작성·유지
  - 임상 데이터 모델 문서, ERD, 접근권한 매트릭스, 환자정보 데이터 흐름도, 감사 로그 정책, AI 요약 승인 흐름도, 환자 안전 알림 규칙 명세, 테스트 시나리오

## B. 이번 학기 설계만 수행 (문서화, 구현은 최소 스텁 또는 없음)

- **FHIR 매핑 명세**: Patient/Encounter/LabResult/Diagnosis/Allergy/Prescription 6종 매핑 문서 작성 (`docs/fhir-mapping-spec.md`). 실 구현은 시간이 허용될 때만 스트레치 목표로 시도 (합성 환자 1명 FHIR Bundle JSON 내보내기)
- **ClinicalNote/AiSummary의 DocumentReference·Provenance 매핑**: 설계 문서에만 포함, 구현 없음
- **개인정보 및 보안 위협 모델**: `docs/security-threat-model.md` 작성 (구현 검증이 아닌 문서 작업으로 완결)
- **AiSummary 상태 확장안**(`PUBLISHED`/`WITHDRAWN` 분리): 설계 문서에만 명시, 구현 없음

## C. 방학 및 4학년 프로젝트 확장

- `AiSummary` 상태를 `APPROVED`/`PUBLISHED`/`WITHDRAWN`으로 실제 분리 구현
- `ClinicalNote`/`AiSummary`의 `DocumentReference`/`Provenance` FHIR 매핑 실제 구현
- 실제 LLM API 연동으로 mock 요약 생성기 교체
- 3개 진료과 이상으로 설정 기반 화면 일반화
- 운영급 인증(SSO/병원 계정 연동), 배포 파이프라인, 감사 로그 저장소 확장성/보존 정책
- FHIR Bundle 내보내기를 ClinicalNote/AiSummary 포함 전 리소스로 확장

## 핵심 시나리오 (완료 기준)

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

## 안전성 원칙 (전 범주 공통 적용)

- AI는 진단하지 않는다.
- AI는 처방을 생성하거나 변경하지 않는다.
- 규칙 엔진은 검토 대상만 표시한다.
- 시스템은 처방을 자동 확정하거나 대체하지 않는다.
- 최종 임상 판단과 처방 결정은 의료진이 수행한다.
- 모든 임상 데이터와 의약품 데이터는 합성 데이터만 사용한다.

## 다음 단계

이 문서는 학기 구현 범위를 확정하는 스코프 문서다. 실제 작업 단위(태스크 분해, 순서, 각 태스크의 완료 조건)를 담은 상세 구현 계획은 착수 시점에 별도로 작성한다.
