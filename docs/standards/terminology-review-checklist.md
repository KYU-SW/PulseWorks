# 표준 용어 전문가 검토 체크리스트

이 문서는 `kr-cdi-kr-core-mapping.md`에서 "C(전문가 확인 필요)" 또는
"확인 필요"로 남긴 항목을 실제 검토가 가능한 형태로 모은 요청 목록이다.
**이 문서 자체는 코드값을 제안하지 않는다** — 각 항목에 대해 검토자가
채워야 할 빈 칸만 제공한다.

작성일: 2026-11-05 (1차) / 2026-11-05 근거 보강(2차 — KR Core IG v1.0.2 공식
페이지 직접 확인 반영. 아래 각 항목에 "(v1.0.2 확인 완료, 코드값만 필요)"로
표시된 것은 **어떤 코드체계를 써야 하는지는 이미 공식 확인됐고, 개별 코드값만
전문가가 정하면 되는 상태**다.)

근거 문서: `kr-cdi-kr-core-mapping.md`

## 1. 의료진(임상) 검토 요청

| 항목 | 질문 | 검토자 입력란 |
|---|---|---|
| 진단 확실성(certainty) | KR Core v1.0.2에서 `Condition.verificationStatus`는 선택 요소로 확인됐다 — 이 프로젝트에서 "확정/추정" 구분을 실제로 둘 가치가 있는가? | |
| 주진단/부진단 구분 | KR Core v1.0.2는 "주호소(Chief Complaint)"와 "진단(Encounter Diagnosis)"을 별도 Profile로 구분하지만, "진단" 안에서의 주/부 구분 요소는 확인되지 않았다 — 이 프로젝트에 필요한가? | |
| onset_date vs diagnosed_at | KR Core v1.0.2의 "진단" Profile도 `recordedDate`("진단일자 및 최초 기록일자")만 필수이고 `onset[x]`는 필수가 아니다 — 그럼에도 "실제 발병 시점"을 별도로 기록해야 하는 진단 유형이 있는가? | |
| 활력징후 측정 맥락 | KR Core v1.0.2의 VitalSign Profile들은 측정 자세·측정 부위에 대한 요건을 명시하지 않는다(혈압의 자세, 체온의 측정 부위 등) — 그럼에도 이 프로젝트에서 반드시 함께 기록해야 하는가? | |
| 수술·시술(Procedure) 최소 필드 | KR Core Procedure Profile은 `status`/`code`(HIRA EDI)/`performed[x]`만 필수다 — 마취 종류, 집도의 등 추가 필드가 이 프로토타입에 필요한가? | |
| 영상 판독문 요약 범위 | KR Core v1.0.2에 DiagnosticReport/ImagingStudy Profile이 4종 존재함은 확인됐으나 세부 Element는 미확인이다 — 환자 화면에 노출할 "판독 요약" 수준을 먼저 정의해 달라(과도한 단정 방지 관점) | |
| 알레르기 중증도 값 불일치 | 현재 내부 `severity`(예: "MODERATE")가 KR Core AllergyIntolerance의 `criticality`(low/high/unable-to-assess, 3개 값)와 **직접 대응하지 않음을 확인했다** — "MODERATE"를 어느 쪽에 매핑해야 하는가, 아니면 별도 값 집합을 유지해야 하는가? | |

## 2. 의무기록(HIM) 전문가 검토 요청

| 항목 | 질문 | 검토자 입력란 |
|---|---|---|
| KR CDI 정확한 분류·항목 수 | 법령 별표 PDF를 여전히 추출하지 못했다 — 현재 KR CDI(V1/V2/V3)의 정확한 Class 수·Element 수는 몇 개인가? | |
| KR CDI V3·KR Core V2 상세설명서 입수 | HINS 사이트(hins.or.kr)가 JavaScript로 렌더링되어 자동 도구로 자료실 위치를 찾지 못했다 — 이 문서(국가보건의료표준 KR CDI V3, KR Core V2 상세설명서)를 직접 찾아 전달해 줄 수 있는가? | |
| ICD-10→KCD-8 매핑 원칙 | KR Core v1.0.2는 KCD-8을 요구한다는 것이 확인됐다 — 현재 seed 데이터의 ICD-10 코드(`E11.9`, `M17.9`, `R07.9`, `Z00.0`)에 대응하는 KCD-8 코드는 무엇인가? | |
| `code_system` 필드 설계 | 코드체계·버전을 명시하는 필드명과 허용값 집합을 어떻게 정의해야 하는가(예: `"ICD-10"`, `"KCD-8"`)? | |
| 의료인 식별자(MOHW 면허번호) | KR Core v1.0.2는 `qualification.identifier` 구조로 **보건복지부(MOHW) 의사면허번호 식별자 체계를 공식 요구**한다(`http://www.hl7korea.or.kr/Identifier/mohw-md-license-id`) — 이 식별자의 정확한 자릿수·포맷은 무엇인가? | |
| KCD 현재 차수 재확인 | KR Core IG v1.0.2(2023-2024년 생성)는 KCD-8을 참조하는데, 이전 조사의 언론 보도는 "제9차"를 언급했다 — 2026-11 현재 실무에서 쓰이는 KCD는 몇 차인가? | |

## 3. 임상병리(검사) 전문가 검토 요청

| 항목 | 질문 | 검토자 입력란 |
|---|---|---|
| **LabResult 필수 코드체계 정정(중요)** | KR Core v1.0.2에서 LabResult(Observation)의 **필수 코드체계는 LOINC가 아니라 HIRA EDI 코드**임이 확인됐다(LOINC는 example 수준, 강제 아님) — 이 사실을 알고도 LOINC 매핑이 이 프로젝트에 필요한가, 아니면 HIRA EDI 코드만으로 충분한가? | |
| LabResult→HIRA EDI 매핑(v1.0.2 확인 완료, 코드값만 필요) | 현재 seed 데이터의 검사명(`HbA1c`, `Fasting Glucose` 등)에 대응하는 HIRA EDI 코드는 무엇인가? | |
| LabResult→LOINC 매핑(선택) | (강제는 아니지만) 참고용으로 LOINC 코드도 함께 매핑한다면 무엇인가? specimen·method·timing에 따라 달라질 수 있다는 점 포함 | |
| specimen·method 필드 | KR Core v1.0.2에서 `specimen`은 선택 요소로 확인됐고 `method`는 이번 조사에서 원문을 완전히 대조하지 못했다 — 이 두 필드가 이 프로젝트에 실제로 필요한가? | |
| **활력징후 LOINC 코드(공식 확인 완료 — 재검증만 요청)** | KR Core IG v1.0.2 StructureDefinition 페이지에서 다음 LOINC 코드를 **고정값으로 직접 확인**했다: Blood Pressure 패널 `85354-9`(수축기 `8480-6`/확장기 `8462-4`), Body Height `8302-2`, Body Temperature `8310-5`, Body Weight `29463-7`, Heart Rate `8867-4`, Respiratory Rate `9279-1`, Pulse Oximetry `2708-6`. **BMI는 Profile 자체가 없음을 확인함.** 이 코드들이 임상적으로 올바른지 재검증해 줄 수 있는가? | |
| UCUM 단위 적용 | KR Core v1.0.2는 각 활력징후의 단위 `system`을 UCUM URI(`http://unitsofmeasure.org`)로 고정하고, 혈압은 `mm[Hg]`, 체온은 `Cel`, 나머지는 자연어 단위(`cm`/`kg`/`/min`/`%`)를 code로 고정했다 — UCUM 표기와 실제 측정 관행 사이에 주의할 점이 있는가? | |
| interpretation 세분화 | 현재 `is_abnormal`(불리언) 대신 HIGH/LOW/NORMAL 등을 모델 필드로 둘 때 임상병리 관점에서 추가해야 할 상태값이 있는가? (KR Core v1.0.2 LabResult Profile 페이지에서 `interpretation` 요소 자체를 확인하지 못했음) | |

## 4. 약무 전문가 검토 요청

| 항목 | 질문 | 검토자 입력란 |
|---|---|---|
| **Prescription 필수 코드체계(공식 확인 완료)** | KR Core v1.0.2는 처방 약물에 **HIRA EDI 의약품 코드**(`Medication.code.coding:EDI`, system `http://www.hl7korea.or.kr/CodeSystem/hira-edi-medication`)와 **WHO ATC 성분 코드**(`Medication.ingredient...coding:ATC`, system `http://www.whocc.no/atc`) **두 가지 모두를 required로 요구**함을 확인했다 — 현재 seed 데이터의 약물명(`Metformin` 등)에 대응하는 이 두 코드는 무엇인가? | |
| dosage 구조화 | KR Core MedicationRequest는 `dosageInstruction.timing`, `doseAndRate.doseQuantity`(UCUM preferred), `dispenseRequest.expectedSupplyDuration` 등 상세 구조를 Must Support로 요구한다 — 현재 자유 텍스트(`"1000mg"`)를 이 구조로 분리할 때 필요한 최소 필드는 무엇인가? | |
| **Allergy ATC 필수 규칙(공식 확인 완료)** | KR Core v1.0.2는 `category='medication'`인 알레르기에 **WHO ATC 코드를 invariant(필수 규칙)로 강제**한다 — 현재 seed 데이터의 알레르기 물질(`Penicillin` 등)에 대응하는 ATC 코드는 무엇인가? | |
| Procedure 코드체계(공식 확인 완료) | KR Core Procedure도 LabResult와 **동일한 HIRA EDI 코드체계**(`hira-edi-procedure`)를 required로 요구한다 — 수술·시술명에 대응하는 EDI 코드는 어디서 확인 가능한가? | |

## 5. 개발자 확인/후속 조사 필요 항목 (전문가 검토 전 선행 조사)

| 항목 | 다음 조사 방법 | 상태 |
|---|---|---|
| KR Core IG v1.0.2 공식 Profile 목록·버전 | ~~build.fhir.org 경로~~ | **완료** — https://www.hins.or.kr/nrc_fhir/kr/core/1.0.2/site/ 에서 toc.html 포함 직접 확인함(2026-11-05) |
| "KR CDI V3, KR Core V2 상세설명서" | https://hins.or.kr/ 가 JavaScript 렌더링이라 자동 도구로 메뉴/자료실을 찾지 못했다 — 사용자가 브라우저로 직접 탐색해 정확한 URL을 전달해야 함 | **미완료** |
| KCD 정확한 현재 차수 | 통계청 통계분류포털(kssc.kostat.go.kr)이 TLS 인증서 불일치로 접근 실패 — 다른 경로(보도자료, 통계청 고시 원문)로 재확인 필요. KR Core v1.0.2는 KCD-8을 참조함(간접 증거) | **부분 완료** |
| EMR 인증기준 세부 항목 | https://emrcert.mohw.go.kr/menu.es?mid=a10102010000 (세부내용), https://emrcert.mohw.go.kr/board.es?mid=a10601000000&bid=0003&list_no=1087&act=view (전체보기) — 링크는 확인했으나 본문 미열람 | **미완료** |
| KR Core v1.0.2의 ImagingStudy/DiagnosticReport 세부 Element | toc.html에서 4개 DiagnosticReport Profile + ImagingStudy Profile의 존재만 확인, 개별 StructureDefinition 페이지는 미열람 | **미완료** |
| 간호사(NURSE) 전용 KR Core Profile 존재 여부 | toc.html 목차에 "Medical Doctor" 전용 Practitioner/PractitionerRole만 확인됨 — 간호사용 별도 Profile이 있는지 재확인 필요 | **미완료** |
| LabResult `method`, `interpretation` 요소 | StructureDefinition-krcore-observation-laboratory-result.html의 해당 부분이 자동 요약으로 처리되어 원문 대조를 못함 | **미완료** |
