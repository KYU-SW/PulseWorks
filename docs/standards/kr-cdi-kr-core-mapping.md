# 국내 보건의료표준 매핑 문서 (KR CDI · KR Core · FHIR R4)

**이 문서는 국내 국가보건의료표준과의 매핑 및 변환 가능성을 검토하기 위한
설계 문서다. 이 프로젝트가 KR CDI·KR Core·전자의무기록시스템 인증기준을
완전히 준수한다거나 인증을 획득했다는 선언이 아니며, 이 문서 자체가
인증 신청 문서도 아니다.**

- 작성일: 2026-11-05 (1차 작성) / 2026-11-05 근거 보강(2차, HINS 공식 IG 사이트 직접 확인 반영)
- 범위: Task F1 (매핑 문서 작성)만 승인된 상태. VitalSign·Procedure·
  ImagingStudy·DiagnosticReport 모델 구현, Migration, Evidence Tag 확장,
  Prompt/Validator/Frontend 변경은 이 문서에서 **설계만** 다루며
  아직 어떤 코드도 작성하지 않았다.
- 매핑 신뢰도 분류: **A(공식 확인 — 해당 버전의 공식 원문에서 직접 확인)** /
  **B(FHIR 후보 — HL7 FHIR R4에서 확인했지만 KR Core 적용 여부 미확인)** /
  **C(전문가 확인 필요)** / **D(현재 범위 밖)**. 공식 원문을 직접 열지 못한
  항목은 A로 승격하지 않았다.
- **최신 KCD 차수 미확정**: 통계청(KOSTAT) 1차 출처를 이번 조사에서 직접
  열람하지 못했으므로, 현재 몇 차 KCD가 시행 중인지는 **이 문서가 확정하지
  않는다**(§0·§6 참고). KR Core IG v1.0.2가 참조하는 "KCD-8"은 그 IG의
  생성 시점(2023~2024년) 기준 참조값일 뿐, 통계청의 현재 공식 차수를
  대신하지 않는다.
- **임의 코드 생성 금지**: 이 문서에 등장하는 개별 LOINC·KCD·HIRA EDI·ATC
  코드값은 전부 KR Core IG v1.0.2 공식 페이지에서 **고정값(Fixed Value)으로
  직접 읽은 것**이며, 이 문서를 작성하며 추측하거나 새로 만든 코드는 없다.
  반대로 "확인 필요"로 남은 코드값(예: 세부 ICD-10→KCD-8 대응표, 개별
  검사명·약물명의 실제 코드)은 전문가 확인 전까지 **절대 임의로 채우지
  않았다.**
- **전문가 검토 전 미확정**: C(전문가 확인 필요)로 분류된 모든 항목은
  의료진·의무기록·임상병리·약무 전문가의 실제 검토를 거치기 전까지
  **확정값으로 취급하지 않는다** — 설계 참고용일 뿐, 바로 구현에 반영할
  수 있는 승인된 값이 아니다.
- **버전 분리 원칙**: 이번 보강에서 직접 확인한 것은 **KR Core IG v1.0.2
  (STU1, FHIR R4 기반)** 뿐이다. HINS가 별도로 공지한 "KR CDI V3·KR Core V2
  상세설명서"는 이번 조사에서 그 문서 자체를 찾지 못해 **열람하지 못했다**.
  v1.0.2에서 확인한 내용을 V2의 내용으로 추론하지 않았다 — 아래 매핑표의
  모든 KR Core 관련 등급은 **v1.0.2 기준**이며, 이 버전 표시를 생략하지
  않는다.

## 0. 사용한 공식 출처 (출처명·버전·링크·확인일)

| 출처 | 버전/표기 | 링크 | 확인일 | 확인 방식 |
|---|---|---|---|---|
| **KR Core Implementation Guide (HL7 Korea, HINS 게시)** | **v1.0.2 - STU1**, FHIR R4(4.0.1) 기반, Package `hl7.fhir.kr.core#1.0.2`, "Active as of 2023-12-04"(IG 홈), 각 리소스 페이지는 "Active as of 2024-09-12"로 표시(페이지별 생성일 차이로 추정, 원인 미확인), 발행 HL7 Korea(© 2022+) | https://www.hins.or.kr/nrc_fhir/kr/core/1.0.2/site/ (홈), `/toc.html`(목차), 개별 `StructureDefinition-krcore-*.html` | 2026-11-05 | **직접 fetch 성공 — 목차 1개 + StructureDefinition 20개 + downloads.html 직접 열람**(아래 §1·§2·§3에 반영) |
| HL7 FHIR R4 (Technical Correction) | v4.0.1, 2019-10-30(+정정 2019-11-01) | https://hl7.org/fhir/R4/ | 2026-11-05 | 검색 결과로 버전·날짜 확인(KR Core 페이지들이 동일 버전을 "based on FHIR 4.0.1"로 재확인함) |
| 전자의무기록시스템 인증기준 안내(한국보건의료정보원) | "인증기준" 페이지 | https://www.khis.kr/menu.es?mid=a10201010200 | 2026-11-05 | 직접 fetch로 본문 확인(기능성 27개/상호운용성 20개/보안성 12개, 유형1~3) |
| 2주기 EMR 인증 시범사업 보도자료(보건복지부) | 2024.02.13 | https://m.korea.kr/briefing/pressReleaseView.do?newsId=156615099 | 2026-11-05 | 직접 fetch로 본문 확인(법적근거 의료법 제23조의2, 총 60개=28+20+12, 2025.1~2027.12 제2주기 시행 예정) |
| EMR 인증 세부기준(한국보건의료정보원/보건복지부) | 세부내용 | https://emrcert.mohw.go.kr/menu.es?mid=a10102010000 | 2026-11-05(링크만 확인, 본문 미열람) | 다음 조사 대상 |
| KR CDI 법적 근거 별표(법제처) | PDF(별표, 고시 번호 미확인) | https://www.law.go.kr/LSW/flDownload.do?flSeq=160548287 | 2026-11-05 | fetch는 성공했으나 **PDF가 바이너리(한컴 생성) 압축 스트림이라 본문 텍스트를 추출하지 못함** — "14분류·80항목" 등 구체 수치는 이번 조사에서도 원문으로 확인하지 못했다 |
| "국가보건의료표준(KR CDI V3, KR Core V2) 상세설명서" (HINS) | V3/V2(공지 기준, 미확정) | **찾지 못함** — https://hins.or.kr/ 는 fetch 성공(HTTP 200)했으나 본문이 JavaScript로 렌더링되어 정적 텍스트가 비어 있었음(0자) | 2026-11-05 | **접근 실패 — 자료실/게시판 위치를 특정하지 못했다.** 사용자가 직접 브라우저로 탐색해 정확한 다운로드 URL을 찾아야 한다(§5 참고) |
| LOINC | 버전 2.82(검색 결과 기준, loinc.org 원문 release notes는 직접 열람하지 않아 정확한 발표일은 미확인) | https://loinc.org/kb/loinc-release-notes/ | 2026-11-05 | 버전 번호는 검색 결과로만 확인. **개별 LOINC 코드 중 혈압/신장/체중/체온/맥박/호흡수/산소포화도 코드는 KR Core IG StructureDefinition 페이지에 고정값(Fixed Value)으로 박혀 있어 그 페이지를 통해 간접적으로 공식 확인됨**(§3 참고, 출처는 KR Core IG이지 loinc.org 원문 직접 열람이 아님 — 이 차이를 분리해 표기) |
| DICOM(NEMA PS3 / ISO 12052) | "current" 에디션 표기가 조회 시점마다 다름(2022a/2026b/2026c 혼재 확인) | https://dicom.nema.org/medical/dicom/current/ | 2026-11-05 | 검색 결과로 존재·구조 확인, 특정 에디션 문자는 **확인 필요** |
| **KCD-8 (한국표준질병사인분류 제8차)** | 코드체계 URI `http://www.hl7korea.or.kr/CodeSystem/kostat-kcd-8`, "a valid code from KOSTAT KCD-8" | KR Core IG `StructureDefinition-krcore-condition-encounter-diagnosis.html`의 `code.coding:KCD-8` 슬라이스(필수 바인딩) | 2026-11-05 | **KR Core IG 공식 페이지에서 직접 확인 — "KCD-8"이라는 표기와 통계청(KOSTAT) 코드체계 URI는 확인됐으나, 통계청 자신의 공식 페이지(kssc.kostat.go.kr)는 TLS 인증서 오류로 접근 실패해 "현재 제8차가 맞는지, 더 최신 차수가 있는지"는 KR Core IG 쪽 표기 하나만으로는 확정할 수 없음.** 이전 조사에서 언론 보도는 "제9차"를 언급했으나(미확정), KR Core v1.0.2는 KCD-8을 참조한다 — **두 표기가 다르며, 이는 KR Core IG(2023-2024년 생성)가 더 이전 차수를 참조했을 가능성과 "제9차" 보도 자체의 신뢰도 문제 둘 다 열려 있다는 뜻이다.** 통계청 1차 출처로 재확인 필요 |

**이번 보강에서 새로 직접 확인한 공식 페이지 목록(KR Core IG v1.0.2, 전부 HTTP 200)**:
`index.html`, `toc.html`, `downloads.html`, `StructureDefinition-krcore-patient.html`, `-encounter.html`, `-medical-doctor.html`, `-medical-doctor-role.html`, `-condition-chief-complaint.html`, `-condition-encounter-diagnosis.html`, `-observation-laboratory-result.html`, `-medicationrequest.html`, `-medication.html`, `-allergyintolerance.html`, `-procedure.html`, `-vitalsigns.html`, `-bloodpressure.html`, `-bodyheight.html`, `-bodytemperature.html`, `-bodyweight.html`, `-heartrate.html`, `-pulseoximetry.html`, `-respiratoryrate.html`.

**주의**: 일부 페이지는 길어서 자동 요약(모델 생성 요약)으로 끝부분을 처리한 항목이 있다 — 그런 세부 항목은 아래 표에서 "(요약, 원문 미대조)"로 표시했다. **블로그·개인 게시물·생성형 AI의 자체 종합 답변은 매핑 근거로 사용하지 않았다.**

## 1. 현재 모델 매핑표

열 구성: 내부 모델 / 내부 필드 / 의미 / KR CDI 항목 / KR Core Profile / FHIR Resource / FHIR Element 경로 / 코드체계 / 현재 지원 수준 / 부족한 필드 / 변환 규칙 / 검증 규칙 / 매핑 신뢰도 / 전문가 검토 주체 / 공식 출처

### Patient

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `mrn` | 병원 내부 환자 식별자 | 확인 필요 | **KR Core Patient Profile**(canonical `http://www.hl7korea.or.kr/fhir/krcore/StructureDefinition/krcore-patient`) — `identifier` 1..\*, Must Support(system/value 각각 Must Support) | Patient | `Patient.identifier` | 기관 자체 식별자(KR Core Patient는 식별자 체계를 특정 코드로 고정하지 않음) | 부분 | `identifier.system` 네임스페이스 미정의 | `mrn`→`identifier.value` | 환자당 유일값, `identifier.use` 바인딩 required(IdentifierUse) | **A** | 개발자 | KR Core IG v1.0.2(직접 확인) |
| `full_name` | 환자 성명(합성 데이터) | 확인 필요 | 동일 Profile — `name` 1..\*, Must Support(`name.text` Must Support) | Patient | `Patient.name.text` | 해당 없음 | 지원 | — | 직접 매핑 | `name.use` 바인딩 required(NameUse) | **A** | 개발자 | KR Core IG v1.0.2(직접 확인) |
| `birth_date` | 생년월일 | 확인 필요 | 동일 Profile — `birthDate` 1..1, Must Support | Patient | `Patient.birthDate` | 해당 없음 | 지원 | — | 직접 매핑(`date` 포맷) | ISO 8601 날짜 포맷 | **A** | 개발자 | KR Core IG v1.0.2(직접 확인) |
| `sex` | 성별(자유문자열) | 확인 필요 | 동일 Profile — `gender` 1..1, Must Support | Patient | `Patient.gender` | 바인딩 required(AdministrativeGender) | 부분 | 현재 자유문자열("F"/"M")을 AdministrativeGender ValueSet(male/female/other/unknown)으로 정규화하는 규칙 없음 | 자유문자열→FHIR gender code 매핑표 필요 | ValueSet 포함 여부 | **A**(Profile 요건 확인) / 변환표 자체는 **B** | 개발자 | KR Core IG v1.0.2(직접 확인) |

### User / Staff (Practitioner / PractitionerRole)

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `email`, `full_name` | 의료인 로그인 계정/성명 | 확인 필요 | **KR Core Practitioner Profile for Medical Doctor**(canonical `...StructureDefinition/krcore-medical-doctor`) — `name` 1..\*, Must Support. **`qualification` 1..\*, Must Support**, 그 안의 `qualification.identifier:MOHW`가 **보건복지부 의사면허번호 체계로 고정**(`system` fixed `http://www.hl7korea.or.kr/Identifier/mohw-md-license-id`, Must Support) | Practitioner | `Practitioner.name`, `.qualification.identifier` | **의사면허번호 체계가 KR Core에 명시적으로 정의되어 있음을 공식 확인** — 단, 현재 이 프로젝트 `User` 모델에는 그에 대응하는 필드가 없음 | 미지원(면허번호 식별자) | `qualification.identifier` 구조 전체(MOHW 면허번호) 신규 필드 | 신규 필드 추가 후 매핑. 면허번호 자체의 포맷(자릿수 등)은 이 페이지에 명시되지 않음 | — | **A**(Profile/바인딩 존재는 확인) / 실제 면허번호 포맷은 **C** | 의료진 + 개발자 | KR Core IG v1.0.2(직접 확인) |
| `department`(Enum), `role=DOCTOR` | 진료과, 역할 | 확인 필요 | **KR Core PractitionerRole Profile for Medical Doctor**(canonical `...StructureDefinition/krcore-medical-doctor-role`) — `specialty` 1..\*, Must Support, 그 안의 `specialty.coding:HIRA`가 **건강보험심사평가원(HIRA) 진료과 코드체계로 고정**(`system` fixed `http://www.hl7korea.or.kr/CodeSystem/hira-medical-department`, required 바인딩 "KR Core Medical Department Codes") | PractitionerRole | `PractitionerRole.specialty.coding` | **HIRA 진료과 코드체계가 명시적으로 지정됨을 공식 확인** — 개별 코드값(예: 내분비내과 코드)은 이 페이지에서 확인하지 않았음 | 부분 | `department`(Enum: ENDOCRINOLOGY 등)→HIRA 진료과 코드 매핑표 | Enum→코드 매핑표 완전성 | **A**(코드체계 지정 확인) / 개별 매핑표는 **C** | 의료진 + 개발자 | KR Core IG v1.0.2(직접 확인) |
| `role=NURSE` | 간호사 역할 | 확인 필요 | **확인하지 못함** — KR Core 목차(toc.html)에 "의사(Medical Doctor)" 전용 Practitioner/PractitionerRole Profile만 확인됨, 간호사 전용 Profile이 별도로 존재하는지는 이번 조사에서 확인하지 않았음 | Practitioner, PractitionerRole | — | — | 확인 필요 | — | — | — | C | 개발자(목차 재확인) | KR Core IG v1.0.2 toc.html(간호사 Profile 유무 미확인) |

### Encounter

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `department`, `encounter_type`, `start_time`, `end_time` | 진료 방문 정보 | 확인 필요 | **KR Core Encounter Profile**(canonical `...StructureDefinition/krcore-encounter`) — `status` 1..1 Must Support(바인딩 required, EncounterStatus), `class` 1..1 Must Support(바인딩 **required**, ActEncounterCode — "AMB \| EMER \| IMP +"), `period` 0..1 Must Support(`start`/`end` 각각 Must Support), `type` 0..\*(예시 바인딩만, Must Support 아님) | Encounter | `Encounter.class`, `.period.start/.end` | `class` 바인딩이 ActEncounterCode(국제 HL7 v3 코드)로 **required** — 국내 전용 코드체계는 아님 | 부분 | `encounter_type`(OUTPATIENT/INPATIENT/EMERGENCY)→ActEncounterCode(AMB/IMP/EMER) 매핑표 | Enum→코드 매핑표 완전성 | **A** | 개발자 | KR Core IG v1.0.2(직접 확인) |

### Diagnosis (Condition)

**중요 — 이전 초안에서 "확인 필요"였던 항목이 이번에 A로 승격됨**: KR Core v1.0.2는 Condition을 **두 개의 별도 Profile**로 나눈다 — "주호소"(Chief Complaint)와 "진단"(Encounter Diagnosis). 이 프로젝트의 `Diagnosis` 모델은 둘 중 **진단(Encounter Diagnosis) Profile**에 대응한다.

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `code`(현재 ICD-10 예: `E11.9`) | 진단 코드 | 확인 필요 | **KR Core Condition Profile for Encounter Diagnosis**(canonical `...StructureDefinition/krcore-condition-encounter-diagnosis`) — `code` 1..1 Must Support, 그 안의 **`code.coding:KCD-8` 슬라이스가 1..\*, Must Support, required 바인딩("KR Core KCD8 Codes") — system fixed `http://www.hl7korea.or.kr/CodeSystem/kostat-kcd-8`, "a valid code from KOSTAT KCD-8"** | Condition | `Condition.code.coding` | **KCD-8이 공식적으로 지정된 필수 코드체계임을 KR Core IG 원문에서 직접 확인.** 단 "KCD-8"이 통계청의 현재 최신 차수인지는 통계청 1차 출처로 재확인 필요(위 §0 참고) | 부분(국제 ICD-10만, KCD 미적용) | `code_system` 필드(이 값이 ICD-10인지 KCD-8인지 명시), KCD 버전 필드 | **자동 코드 변환을 제안하지 않음.** `code_system`을 명시적 필드로 추가하고, ICD-10→KCD-8 대응표는 의료진·의무기록 전문가가 직접 확정한 뒤에만 적용 | 코드-체계 일치성, `code_system` 필수 입력 | **A**(필수 코드체계 지정 확인) / 개별 코드 매핑표는 **C** | 의료진 + 의무기록 전문가 | KR Core IG v1.0.2(직접 확인) |
| `description` | 진단명(자유 텍스트) | 확인 필요 | 동일 Profile — `code`는 CodeableConcept이므로 `.text`로 자유 텍스트 수용 가능(페이지에 `code.text` Must Support 여부는 명시되지 않음) | Condition | `Condition.code.text` | 해당 없음 | 지원 | — | 직접 매핑 | — | B | 개발자 | KR Core IG v1.0.2 |
| `diagnosed_at` | 진단 시점 | 확인 필요 | 동일 Profile — **`recordedDate` 1..1, Must Support**, 페이지 설명 "진단일자 및 최초 기록일자" | Condition | `Condition.recordedDate` | 해당 없음 | 지원(단, "발병 시점"과 "기록 시점"이 이 Profile에서도 분리되지 않음 — `onset[x]`는 이 Profile의 Must Support 목록에 없음) | **`onset_date`(실제 발병 시점) 필드 없음** | 직접 매핑 | — | **A** | 의료진 | KR Core IG v1.0.2(직접 확인) |
| (없음) | 진단 확실성 | 확인 필요 | 동일 Profile — `verificationStatus` 0..1, **Must Support 아님**, 바인딩 required(ConditionVerificationStatus) | Condition | `Condition.verificationStatus` | FHIR ConditionVerificationStatus(국제) | **미지원**(필드 자체도 KR Core가 필수로 요구하지 않음) | `certainty`(확정/추정) 필드 전체 | 신규 필드 추가(선택적) | — | **A**(요건이 "선택"임을 확인) | 의료진 | KR Core IG v1.0.2(직접 확인) |
| (없음) | 주진단/부진단 구분 | 확인 필요 | **다른 Profile(주호소/진단)로 구분** — `category:EnctrDiag` 슬라이스가 "진단"임을 고정 코드(`http://www.hl7korea.or.kr/fhir/krcore/CodeSystem/krcore-condition-category-types`, code `진단`)로 표시. 단 "진단" 내부에서 주진단/부진단을 더 세분하는 요소는 이 페이지에서 확인하지 않았음 | Condition | `Condition.category` | KR Core 자체 CodeSystem(국내 전용) | **부분**(주호소 vs 진단은 구분되나, 진단 내 주/부 구분은 미지원) | `diagnosis_type`(주/부) 필드 | 신규 필드 추가(필요시) | — | **A**(주호소/진단 구분 자체는 확인) / 주·부진단 세분화는 **C** | 의료진 | KR Core IG v1.0.2(직접 확인) |

### LabResult (Observation)

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `test_name`(로컬 검사명, 예: "HbA1c") | 검사 항목명 | 확인 필요 | **KR Core Observation Profile for Laboratory Result**(canonical `...StructureDefinition/krcore-observation-laboratory-result`) — `code` 1..1(Must Support 플래그는 명시 안 됨, Σ만). **중요: LOINC 바인딩은 example 강도(강제 아님)**. 대신 `code.coding:EDI` 슬라이스(0..\*, Must Support)가 **건강보험심사평가원(HIRA) EDI 코드로 required 바인딩**, system fixed `http://www.hl7korea.or.kr/CodeSystem/hira-edi-procedure` | Observation | `Observation.code.coding` | **실제 필수 코드체계는 LOINC가 아니라 HIRA EDI 코드임을 공식 확인** — 이전 초안의 "LOINC 매핑"이라는 전제 자체를 수정해야 함 | 부분(로컬 명칭만) | `standard_code`(HIRA EDI), `standard_code_system` | 로컬 검사명→HIRA EDI 코드 매핑표는 **임상병리 전문가(또는 보험청구 전문가) 확인 전까지 비워둠**. LOINC는 보조적·선택적으로만 추가 가능 | 코드 존재 여부(전문가 확정 후) | **A**(필수 코드체계가 LOINC가 아니라 HIRA EDI라는 사실 확인) | 임상병리 전문가 + 보험청구(HIRA EDI) 확인 가능자 | KR Core IG v1.0.2(직접 확인) |
| `value`, `unit` | 검사값·단위 | 확인 필요 | 동일 Profile — `value[x]` 0..1, Must Support. `valueQuantity`의 `unit`은 example 바인딩(자유), **`system`은 `http://unitsofmeasure.org`로 고정**(즉 UCUM 시스템 URI 적용) | Observation | `Observation.valueQuantity.value/.unit` | **UCUM이 system URI로 적용됨을 공식 확인**(페이지 본문에 "UCUM"이라는 단어 자체는 나오지 않지만, system이 UCUM의 공식 네임스페이스로 고정되어 있어 실질적으로 UCUM 적용으로 해석됨) | 부분 | UCUM 코드값 자체(예: `%`→`%`, `mg/dL`→UCUM 표기) | `unit`(자유문자열)→UCUM 코드 매핑 | 단위 유효성 | **A**(UCUM 시스템 적용 확인) / 개별 단위 코드 매핑은 **C** | 임상병리 전문가 | KR Core IG v1.0.2(직접 확인) |
| `reference_low`/`reference_high` | 참고범위 | 확인 필요 | 동일 Profile — `referenceRange` 0..\*, Must Support | Observation | `Observation.referenceRange.low/.high` | 해당 없음 | 지원 | — | 직접 매핑 | — | **A** | 개발자 | KR Core IG v1.0.2(직접 확인) |
| `is_abnormal`(불리언) | 이상 여부 | 확인 필요 | 동일 Profile 페이지에서 `interpretation`은 확인하지 못함(원문에 등장하지 않음) | Observation | `Observation.interpretation` | FHIR observation-interpretation(국제, 이 Profile에서의 요건은 미확인) | 부분 | HIGH/LOW/NORMAL 세분화는 애플리케이션 로직(`evaluate_lab_abnormal`)에만 있고 모델 필드로는 없음 | 불리언→interpretation 코드 매핑 | — | C | 개발자 | 확인 필요(이 Profile 페이지에 없음) |
| (없음) | 검체 종류 | 확인 필요 | 동일 Profile — `specimen` 0..1, **Must Support 플래그 없음** | Observation | `Observation.specimen` | 확인 필요 | 미지원(선택 요소) | `specimen` 필드 전체(선택적) | 신규 필드 추가(필요시) | — | **A**(요소 존재·선택 요건 확인) | 임상병리 전문가 | KR Core IG v1.0.2(직접 확인) |
| (없음) | 검사 방법 | 확인 필요 | 동일 Profile — `method`는 이번 조사의 verbatim 텍스트에서 확인하지 못함(요약 처리됨) | Observation | `Observation.method` | 확인 필요 | 미지원 | `method` 필드 전체 | 신규 필드 추가 | — | C(요약 처리, 원문 미대조) | 임상병리 전문가 | KR Core IG v1.0.2(요약, 원문 미대조) |

### Prescription (MedicationRequest / Medication)

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `medication_name`(자유 텍스트, 예: "Metformin") | 약물명 | 확인 필요 | **KR Core MedicationRequest Profile** — `medication[x]` 1..1 Must Support, 타입이 **`Reference(KR Core Medication Profile)`만 허용**(`medicationCodeableConcept`은 이 Profile에 없음 — 반드시 별도 Medication 리소스를 참조해야 함). **KR Core Medication Profile**의 `code` 1..1 Must Support, 그 안의 **`code.coding:EDI` 슬라이스가 required 바인딩으로 건강보험심사평가원 의약품 보험 코드체계**(system fixed `http://www.hl7korea.or.kr/CodeSystem/hira-edi-medication`, "건강보험심사평가원 의약품 보험 코드체계")로 고정. 추가로 **`ingredient.item[x].coding:ATC`가 WHO ATC 코드로 required 바인딩**(system fixed `http://www.whocc.no/atc`) | MedicationRequest, Medication | `MedicationRequest.medication`→`Medication.code.coding`(EDI), `Medication.ingredient.itemCodeableConcept.coding`(ATC) | **필수 코드체계가 HIRA EDI 의약품 코드 + WHO ATC(성분) 2종임을 공식 확인** — "국내 의약품 표준코드를 추측하지 말라"는 지시와 별개로, **어떤 코드체계를 써야 하는지 자체는 공식 문서에서 확인된 사실**임 | 부분(자유 텍스트만) | `standard_code`(HIRA EDI), `ingredient_atc_code`(WHO ATC) | 약물명→두 코드체계 매핑표는 **약무 전문가 확인 전까지 비워둠**(코드체계 종류는 확인됐으나 개별 코드값은 미확인) | 코드 유효기간(전문가 확정 후) | **A**(코드체계 종류 확인) / 개별 코드값 매핑은 **C** | 약무 전문가 | KR Core IG v1.0.2(직접 확인) |
| `dosage`(자유 텍스트, 예: "1000mg") | 용량 | 확인 필요 | 동일 Profile — `dosageInstruction` 1..\*, Must Support. 하위에 `timing`(Must Support), `doseAndRate.doseQuantity`(Must Support, UCUM preferred 바인딩), `dispenseRequest.expectedSupplyDuration`(Must Support, UnitsOfTime required) 등 상세 구조 존재 | MedicationRequest | `MedicationRequest.dosageInstruction` | UCUM(preferred, 강제 아님) | 부분 | 구조화된 용량·투여경로·투여주기 필드 없음(현재 자유 텍스트 1개 필드) | 자유 텍스트→구조화 Dosage 매핑(전문가 확인 필요) | — | **A**(구조 확인) / 실제 매핑은 **C** | 의료진 + 약무 전문가 | KR Core IG v1.0.2(직접 확인) |
| `prescribed_at`, `prescribed_by_user_id` | 처방 시점/처방자 | 확인 필요 | 동일 Profile — `authoredOn`(페이지 verbatim에서 Must Support 여부 미확인), `status`/`intent`는 Must Support(각각 required 바인딩, 선호값 "completed"/"order") | MedicationRequest | `.authoredOn`, `.requester` | 해당 없음 | 지원 | — | 직접 매핑 | — | B | 개발자 | KR Core IG v1.0.2 |

### Allergy (AllergyIntolerance)

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `substance`(자유 텍스트) | 알레르기 유발 물질 | 확인 필요 | **KR Core AllergyIntolerance Profile** — `code` 1..1 Must Support(기본 바인딩 example). **조건부 필수 규칙(invariant `krcore-alrg-01`, error 수준)**: `category = 'medication'`일 때 반드시 `code.coding`에 **WHO ATC 코드**가 있어야 함(`code.coding:ATC` 슬라이스, Must Support, required 바인딩, system fixed `http://www.whocc.no/atc`) | AllergyIntolerance | `.code.coding` | **약물 알레르기인 경우 ATC 코드가 공식적으로 필수(invariant로 강제)임을 확인** — 음식/환경 알레르기는 이 요건이 적용되지 않음(`category`가 다름) | 부분 | 구조화 코드(약물 알레르기는 ATC 필수, 그 외는 선택) | **자유 텍스트 보존을 기본으로 하되, `category=medication`인 경우에만 ATC 코드가 필수가 된다는 조건부 규칙을 설계에 반영** | `code.text` 항상 유지, `category='medication'`→ATC 코드 존재 검증 | **A**(조건부 필수 규칙 자체는 확인) / 실제 ATC 코드값은 **C** | 의료진 + 약무 전문가 | KR Core IG v1.0.2(직접 확인) |
| `reaction`(자유 텍스트) | 반응 | 확인 필요 | 동일 Profile — `reaction.manifestation` 1..\*, **Must Support 플래그 없음**, 바인딩 example(SNOMED CT) | AllergyIntolerance | `.reaction.manifestation` | SNOMED CT(국제, 강제 아님) | 부분 | 구조화 코드(선택적) | 자유 텍스트 유지가 기본, 구조화는 선택 | — | **A** | 의료진 | KR Core IG v1.0.2(직접 확인) |
| `severity` | 중증도 | 확인 필요 | 동일 Profile — 페이지에서 확인한 것은 `criticality`(Σ, Must Support 플래그 없음, required 바인딩: low \| high \| unable-to-assess)이며 **FHIR의 `reaction.severity`(mild/moderate/severe)와는 다른 요소**임을 주의 | AllergyIntolerance | `.criticality` | required 바인딩(AllergyIntoleranceCriticality) | 부분 | 내부 Enum("MODERATE" 등)→`criticality`(low/high/unable-to-assess) 매핑표. **주의: 내부 "MODERATE"가 FHIR `criticality`의 3개 값 중 어디에도 직접 대응하지 않음** — 별도 판단 필요 | Enum→코드 매핑, 값 집합 불일치 해소 방안 | **A**(요소 존재 확인, 단 값 집합 불일치라는 문제 자체를 발견) | 의료진 | KR Core IG v1.0.2(직접 확인) |

### ClinicalReport (의료진 검토·승인 메타데이터)

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `created_by_user_id`, `reviewed_by_user_id`, `reviewed_at`, `status` | 생성·검토·승인 이력 | 확인 필요 | 확인 필요(KR Core IG toc.html에 Provenance Profile은 목록에 없었음 — KR Core v1.0.2가 Provenance를 다루는지 자체가 미확인) | Provenance(개념적으로 가장 근접, FHIR 표준 Resource) | `Provenance.agent`, `.recorded`, `.activity` | 해당 없음 | 부분(개념 대응, 형식은 FHIR Provenance 아님) | 실제 Provenance 포맷으로의 변환 로직 전체 | `created_by_user_id`→`agent`(author), `reviewed_by_user_id`→`agent`(reviewer), `reviewed_at`→`.recorded` | — | B(FHIR 표준 자체는 확인, KR Core v1.0.2에서의 Profile 유무는 미확인) | 개발자 | HL7 FHIR R4 |
| `content.narrative`, `narrative_source`, `narrative_edited_by_clinician` | AI/의료진 작성 설명문과 출처 추적 | 확인 필요 | 해당 없음(FHIR/KR Core 표준 Resource에 직접 대응하는 요소 없음) | 해당 없음 | — | 해당 없음 | **D(현재 범위 밖)** — 이 프로젝트 고유의 Human-in-the-Loop 설계 | — | — | — | D | — | 해당 없음 |

### AiSummary

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `summary_text`, `source_record_ids`, `status` | AI/Mock이 생성한 설명문 초안과 근거 레코드 | 확인 필요 | 해당 없음 | 해당 없음 | — | 해당 없음 | **D(현재 범위 밖)** | — | — | — | D | — | 해당 없음 |

### AuditLog

| 내부 필드 | 의미 | KR CDI 항목 | KR Core Profile | FHIR Resource | FHIR Element 경로 | 코드체계 | 현재 지원 수준 | 부족한 필드 | 변환 규칙 | 검증 규칙 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `actor_user_id`, `action`, `reason`, `created_at` | 주요 작업 감사 기록 | 전자의무기록시스템 인증기준의 "감사기록" 영역과 개념적으로 대응 | 확인 필요(KR Core toc.html에 AuditEvent Profile은 목록에 없었음) | AuditEvent(개념적으로 가장 근접, FHIR 표준) | `AuditEvent.agent`, `.type/.subtype`, `.recorded` | 해당 없음 | 부분(개념 대응) | `action` 문자열 값 집합→AuditEvent 코드 매핑표 전체 | `action`(문자열)→AuditEvent `.type`/`.subtype` 매핑 | 매핑표 완전성 | B | 개발자 | HL7 FHIR R4 |

## 2. 확장 후보 모델 매핑 — VitalSign(공식 확인, 대폭 갱신) / Procedure / Imaging

### VitalSign — **KR Core v1.0.2에 공식 Profile이 실제로 존재함을 확인**

8개 중 **7개**(BMI 제외)가 KR Core IG v1.0.2에 **실제 Profile로 존재**하며, 전부 LOINC 코드가 **고정값(Fixed Value)**으로 지정되어 있다. 상세는 §3.

| 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|
| Blood Pressure / Body Height / Body Temperature / Body Weight / Heart Rate / Pulse Oximetry / Respiratory Rate (7종) | **각각 공식 Profile 존재**("KR Core Observation Profile for Vital Signs: ___") — 전부 `KRCore_Observation_VitalSigns`(공통 상위 Profile)를 상속 | Observation(vital-signs 카테고리, 공통 상위 Profile이 `category` 슬라이스를 `vital-signs`로 고정) | `.code.coding:Loinc`(고정 LOINC 코드), `.component`(혈압만 2개 필수), `.valueQuantity` | **LOINC가 각 Profile에 고정값으로 지정됨**(§3 코드값 참고). 단위의 `system`은 `http://unitsofmeasure.org`(UCUM)로 고정 | **A** | 임상병리 전문가(코드 재확인), 개발자 | KR Core IG v1.0.2(직접 확인, StructureDefinition 8개 페이지) |
| BMI | **공식 Profile이 존재하지 않음**(toc.html 목차에 없음, 다른 7종과 달리 KR Core v1.0.2가 별도 Profile로 다루지 않음) | 해당 없음(계산값이므로 Height/Weight로부터 애플리케이션에서 파생 가능) | — | — | **A**(부재 확인) | 개발자 | KR Core IG v1.0.2 toc.html(직접 확인) |

### Procedure

| 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|
| 수술·시술명, 시행일 | **KR Core Procedure Profile** — `status`(1..1, Must Support, required, 선호값 "completed"), `code`(1..1, Must Support, 기본 바인딩 example), **`code.coding:EDI` 슬라이스가 required 바인딩으로 HIRA EDI 수술·처치 코드**(system fixed `http://www.hl7korea.or.kr/CodeSystem/hira-edi-procedure` — LabResult와 **동일한 코드체계**), `subject`(1..1), `performed[x]`(1..1, Must Support, dateTime 등 5종 허용) | Procedure | `.code.coding`(HIRA EDI), `.performedDateTime` | **HIRA EDI 코드가 필수 코드체계임을 공식 확인**(LabResult와 체계 공유) | **A**(코드체계 확인) / 개별 코드값은 **C** | 의료진(수가 코드 확인 가능자) | KR Core IG v1.0.2(직접 확인) |

### ImagingStudyMetadata / DiagnosticReport

| 항목 | KR Core Profile(v1.0.2) | FHIR Resource | FHIR Element 경로 | 코드체계 | 신뢰도 | 검토 주체 | 공식 출처 |
|---|---|---|---|---|---|---|---|
| 영상 모달리티, 판독문 | **toc.html에서 Profile 자체의 존재는 확인됨** — "KR Core DiagnosticReport Profile for Diagnostic Imaging/Function Tests/Laboratory Results/Pathology Results"(4종) + "KR Core ImagingStudy Profile" 전부 목차에 있음. **단, 이번 보강에서 개별 StructureDefinition 페이지는 열지 않았다**(§6의 예산 범위 밖) | ImagingStudy, DiagnosticReport | `.series`, `.conclusion` | DICOM(NEMA PS3/ISO 12052 — 존재·구조만 확인, 특정 에디션 미확정) | **B**(Profile 존재는 목차로 확인, 세부 Element는 미확인) / PACS·실제 DICOM 파일 자체는 **D** | 의료진 + 영상의학 전문가 | KR Core IG v1.0.2 toc.html(목차만 확인), DICOM(dicom.nema.org, 구조만 확인) |

## 3. VitalSign 우선 범위 (F4 설계를 위한 선행 분류) — **공식 확인 완료**

| 항목 | Observation 유형 | 복수 component | 계산값 여부 | 단위(공식, system=UCUM URI 고정) | 측정 시각 | 측정 자세·방법 등 추가 맥락 | **LOINC 코드(공식, Fixed Value)** |
|---|---|---|---|---|---|---|---|
| Blood Pressure | 복수 component(패널) | **예** — `component:Systolic`(1..1), `component:Diastolic`(1..1) | 아니오 | `mmHg`(system `unitsofmeasure.org`, **code `mm[Hg]` 고정**) | Must Support(`effective[x]`, 공통 상위 Profile) | 확인 필요(이 Profile 페이지에 자세 요구사항은 없음) | **패널: `85354-9`** / 수축기 `8480-6` / 확장기 `8462-4` |
| Body Height | 단일 값 | 아니오 | 아니오 | `cm`(code `cm` 고정) | 동일 | 불필요 | **`8302-2`** |
| Body Weight | 단일 값 | 아니오 | 아니오 | `kg`(code `kg` 고정) | 동일 | 불필요 | **`29463-7`** |
| **BMI** | **해당 Profile 자체가 KR Core v1.0.2에 없음** | — | 예(Height/Weight 계산값) | — | — | — | **없음(공식 미지원 확인)** |
| Temperature | 단일 값 | 아니오 | 아니오 | `℃`(code `Cel` 고정) | 동일 | 확인 필요(측정 부위는 페이지에 명시 없음) | **`8310-5`** |
| Heart Rate | 단일 값 | 아니오 | 아니오 | `/min`(code `/min` 고정) | 동일 | 불필요 | **`8867-4`** |
| Respiratory Rate | 단일 값 | 아니오 | 아니오 | `/min`(code `/min` 고정) | 동일 | 불필요 | **`9279-1`** |
| Pulse Oximetry | 단일 값(component도 동일 코드로 존재 가능) | 아니오(요약 처리, 원문 미대조) | 아니오 | `%`(code `%` 고정) | 동일 | 확인 필요(흡입 산소 여부는 페이지에 명시 없음) | **`2708-6`** |

**출처**: 전부 KR Core IG v1.0.2의 해당 StructureDefinition 페이지에서 **직접 확인**(code.coding:Loinc.code가 Fixed Value로 박혀 있음). LOINC 코드의 1차 출처는 loinc.org이지만, 이번 조사는 loinc.org 원문이 아니라 **KR Core IG가 그 코드를 고정값으로 인용한 것**을 확인한 것이다 — 이 차이를 분리해 표기한다. 혈압 외 7종은 `component` 구조가 아니라 단일 `value[x]`(Quantity) 구조다. **"측정 자세·방법 등 추가 맥락"은 KR Core Profile 페이지에 명시적 요구사항이 없음을 확인했다** — 즉 공식 표준이 이를 강제하지 않으므로, 이 프로젝트가 자세·방법을 기록할지는 의료진 판단(§6 참고)이다.

## 4. 코드체계 원칙 (갱신)

- **Diagnosis**: 현재 `Diagnosis.code`의 ICD-10 값(예: `E11.9`)을 KCD-8과 동일한 것으로 간주하지 않는다. KR Core v1.0.2는 **KCD-8을 필수 코드체계로 요구함을 공식 확인**했으나, 통계청이 현재 몇 차 분류를 시행 중인지는 별도로 재확인해야 한다(§0). `code_system`/`code_system_version` 필드를 분리해, 이 코드가 ICD-10/KCD-8/그 이후 차수 중 무엇인지 항상 명시한다. **ICD-10→KCD 자동 변환은 제안하지 않는다.**
- **LabResult**: **검사명만으로 LOINC 코드를 확정하지 않는다 — 더 중요하게는, KR Core v1.0.2 자체가 LabResult에 LOINC를 필수로 요구하지 않고 HIRA EDI 코드를 필수로 요구함을 확인했다.** 임상병리 전문가뿐 아니라 보험청구 코드(HIRA EDI)를 확인할 수 있는 사람의 검토가 함께 필요하다.
- **Prescription**: 약물명을 보고 국내 의약품 표준코드를 추측하지 않는다. **다만 어떤 코드체계(HIRA EDI 의약품 코드 + WHO ATC)를 써야 하는지는 공식 확인됐다** — 개별 코드값만 약무 전문가 확인 전까지 비워둔다.
- **Allergy**: 자유 텍스트(`substance`/`reaction`) 보존을 기본으로 하고, 구조화 코드는 선택적 추가 필드로 설계한다. **단, 약물 알레르기(`category='medication'`)인 경우 KR Core v1.0.2가 WHO ATC 코드를 invariant로 강제함을 확인했다** — 이 조건부 필수 규칙은 설계에 반영해야 한다.

## 5. "KR CDI V3·KR Core V2 상세설명서" 탐색 결과 — 찾지 못함

- 시도한 URL: `https://hins.or.kr/`(HTTP 200이지만 정적 HTML 본문이 비어 있음 — JavaScript로 렌더링되는 사이트로 추정, WebFetch 도구로는 내부 메뉴/게시판 링크를 읽을 수 없었다).
- 이번 보강에서 직접 열람에 성공한 것은 **`hins.or.kr/nrc_fhir/kr/core/1.0.2/site/` 하위의 KR Core IG v1.0.2(STU1)뿐**이며, 이것은 V2가 아니다.
- "KR CDI V3, KR Core V2 상세설명서"는 **HINS의 다른 섹션(자료실/게시판으로 추정)에 있을 가능성이 높으나, 정확한 URL을 찾지 못했다.** 사용자가 브라우저로 직접 접속해(JavaScript 렌더링이 필요하므로) 메뉴를 따라가 정확한 다운로드 링크를 찾아야 한다.
- **다운로드한 공식 파일은 없다.** 저작권·재배포 조건 확인도 당연히 진행하지 않았다(파일 자체를 찾지 못했으므로). `docs/standards/sources/` 디렉터리도 아직 만들지 않았다 — 실제 파일이 확보되기 전까지는 빈 디렉터리를 먼저 만들 이유가 없다고 판단했다.

## 6. KCD 처리 (갱신)

- 공식 자료 URL: https://kssc.kostat.go.kr (TLS 인증서 불일치로 접근 실패, 재시도하지 않음) / https://kcdcode.kr/mobile/aboutKcd (HTTP 200이지만 JavaScript 렌더링이라 본문 거의 없음)
- 접근 성공 여부: **통계청 1차 출처 접근 실패.** 다만 KR Core IG v1.0.2(HINS/HL7 Korea 공식 게시물)가 `kostat-kcd-8`이라는 코드체계 URI를 명시적으로 참조하는 것은 확인됨(§0, §1 Diagnosis 참고) — 이는 "통계청이 KCD-8을 발행했다"는 사실의 **간접 증거**이지, 통계청 자신의 공식 발표문은 아니다.
- 확인 가능한 시행일: 없음(통계청 1차 출처 미접근).
- 확인하지 못한 항목: KCD의 정확한 현재 최신 차수(제8차가 KR Core IG 생성 시점인 2023-2024년 기준인지, 그 이후 더 최신 차수가 있는지), 정확한 시행일.
- **HIM 전문가에게 문의할 내용**: "현재(2026-11) 실무에서 사용 중인 KCD 차수는 몇 차인가? KR Core IG v1.0.2가 참조하는 KCD-8이 여전히 유효한가, 아니면 그 이후 개정(예: 제9차)으로 대체되었는가?"
- **현재 seed의 ICD-10 형식 코드는 여전히 KCD 코드로 간주하지 않는다.**

## 7. 이번 문서에서 여전히 확인하지 못한 항목 (요약, 갱신)

- "KR CDI V3, KR Core V2 상세설명서" 원문(§5) — 위치를 찾지 못함.
- KCD의 정확한 현재 차수·시행일(통계청 1차 출처 미접근, §6).
- KR Core v1.0.2의 ImagingStudy/DiagnosticReport 4종 Profile의 세부 Element(목차에서 존재만 확인, 상세 미확인).
- 간호사(NURSE) 전용 KR Core Profile 존재 여부.
- LabResult `method`, Observation `interpretation`의 KR Core v1.0.2 요건(원문 일부가 요약 처리되어 미대조).
- 개별 HIRA EDI 코드값, WHO ATC 코드값, KCD-8 개별 진단 코드값 — 전문가 확인 전까지 의도적으로 비워둠.

이 항목들은 `terminology-review-checklist.md`에 전문가 검토 요청 목록으로 정리했다.
