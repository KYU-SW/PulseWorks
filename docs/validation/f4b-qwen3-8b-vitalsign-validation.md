# F4-B qwen3:8b 활력징후 설명문 검증 결과

프로젝트: 근거 기반 환자용 임상보고서 지원 웹 EMR 시스템
(Web-Based EMR System for Evidence-Grounded Patient Clinical Reports)

작성일: 2026-11-05

## 1. 검증 목적

Task F4-B(VitalSign의 진료참고 보고서 통합)에서 구현한 실제 LLM 경로
(`RealLLMProvider` + `build_narrative_prompt()`)가, Mock Provider로는
확인할 수 없는 실제 로컬 LLM(qwen3:8b)의 출력에 대해서도 다음을
만족하는지 1회 통합 호출로 확인한다.

- VitalSign 수치·단위가 Snapshot과 정확히 일치하는 narrative를
  생성하는지
- 익명 Evidence Tag(V 태그)가 narrative 본문에 누출되지 않고 올바르게
  근거로 연결되는지
- BMI·품질 경고·내부 식별자 등 환자에게 절대 노출되어서는 안 되는
  정보가 섞여 들어가지 않는지
- 자유서술 영역에 원본 자료에 없는 임상적 해석·인과관계가 섞여
  들어가는지(결정적 Validator로는 확인할 수 없는 의미 수준 위험)

## 2. 검증 범위

- 대상 기능: Task F4-B(VitalSign Clinical Report Integration)의 실제
  LLM Provider 경로
- 검증 방식: 실제 호출 **1회**에 대한 자동 검증(결정적 Validator 수준)
  + 수동 검토(자유서술 의미 수준)
- 범위 밖: 다른 Encounter·다른 환자에 대한 반복 검증, 통계적 신뢰도
  평가, 다른 로컬 모델과의 비교, 실시간 프로덕션 트래픽 검증

## 3. 합성 입력 데이터

- 합성 환자: `SYN-0001` (교육용 합성 데이터, 실제 개인정보 아님)
- 대상 Encounter: 2026-03-10 내분비내과(ENDOCRINOLOGY) 외래
- 포함된 VitalSign: 7종 전부(혈압, 키, 체중, 체온, 맥박, 호흡수,
  산소포화도) — 모두 canonical 단위
- 함께 포함된 자료: 진단 1건(2형 당뇨병), 검사결과(HbA1c, 공복혈당),
  처방 기록, 알레르기 기록

## 4. 실행 조건

- 모델: 로컬 Ollama `qwen3:8b` (Q4_K_M 양자화, 8.2B 파라미터)
- 실행 위치: Windows 호스트에서 구동된 Ollama, Docker backend 컨테이너가
  `host.docker.internal`을 통해 호출
- `NARRATIVE_PROVIDER=llm`, `LLM_VENDOR=ollama`, `LLM_MODEL=qwen3:8b`
- Backend LLM 호출 timeout: 30초 / Frontend 생성 요청 timeout: 75초
- 검증 완료 후 `NARRATIVE_PROVIDER`는 `mock`으로 복귀시켰다(이 설정은
  실험 전용이며 기본값이 아니다)

## 5. 생성 결과 요약

> 환자는 2026년 3월 10일 내분비내과 외래를 방문한 것으로 확인됩니다.
> 당시 측정된 혈압은 120/80mmHg로 정상 범위에 속합니다. 키는 170cm,
> 체중은 65kg로 기록되어 있으며, 체온은 36.5°C, 맥박은 72회/분, 호흡수는
> 16회/분, 산소포화도는 98%로 모두 정상 범위에 해당합니다. 검사 결과에서
> HbA1c는 7.2%로, 정상 범위인 4.0~6.0%보다 높게 나타났습니다. 또한
> 공복혈당은 130mg/dL로, 정상 범위인 70~100mg/dL보다 높게 측정되었습니다.
> 이에 따라 2형 당뇨병이 신규 진단되었습니다. 처방으로는 메트포르민
> 500mg, 펜실린 V 500mg, Task10VerifyNonConflictMedX 1정이 처방되었습니다.
> 펜실린 알레르기로 두드러기 반응이 있는 것으로 기록되어 있습니다.

- 실제 호출 횟수: **1회**
- 결과 보고서 상태: **REJECTED** (이 검증 목적으로 생성된 보고서이며,
  의료진이 실제로 승인하지 않음 — 아래 §9~10 참고)

## 6. 자동 검증 결과

| 항목 | 결과 |
|---|---|
| 구조화 출력(JSON) 파싱 | 성공 |
| 혈압 120/80 mmHg 일치 | 성공 |
| 신장 170 cm 일치 | 성공 |
| 체중 65 kg 일치 | 성공 |
| 체온 36.5°C 일치 | 성공 |
| 맥박 72회/분 일치 | 성공 |
| 호흡수 16회/분 일치 | 성공 |
| 산소포화도 98% 일치 | 성공 |
| VitalSign 근거 7건 연결 | 성공 |
| 내부 V Evidence Tag 미노출 | 성공 (narrative 본문에 `V1` 등 텍스트 없음) |
| 내부 DB 식별자 미노출 | 성공 (`vital_sign:{id}` 형태 원문 없음) |
| BMI 미노출 | 성공 |
| 품질 경고 미노출 | 성공 |
| 치료·약물 변경 지시 없음 | 성공 |
| 부분 저장 없음 | 성공 |

## 7. 수동 검토 결과

**지적 1 — 근거 없는 정상/비정상 판정**

> "혈압은 120/80mmHg로 정상 범위에 속합니다."
> "체온은 36.5°C, 맥박은 72회/분, 호흡수는 16회/분, 산소포화도는 98%로
> 모두 정상 범위에 해당합니다."

VitalSign Snapshot에는 참고범위나 판정(interpretation) 필드가 존재하지
않는다(F4-A 설계상 품질 경고는 의사 화면에서만 계산되고 저장되지 않음).
그런데도 모델이 "정상 범위"라는 임상적 판정을 자체적으로 추가했다.

권장 수정:
> "혈압은 120/80 mmHg, 체온은 36.5℃, 맥박은 72회/분, 호흡수는 16회/분,
> 산소포화도는 98%로 기록되어 있습니다."

**지적 2 — 원본에 없는 인과관계**

> "이에 따라 2형 당뇨병이 신규 진단되었습니다."

진단 기록 자체는 Snapshot에 존재하지만, "검사결과 때문에 진단되었다"는
인과관계는 원본 자료에 명시되어 있지 않다.

권장 수정:
> "검사결과와 함께 2형 당뇨병 신규 진단 기록이 등록되어 있습니다."

## 8. 기술적 통과 항목

§6의 15개 항목 전부 통과. 수치·단위·혈압 두 component·VitalSign
근거 연결·내부정보(V 태그, DB 식별자, BMI, 품질 경고) 차단·치료 지시
배제·부분 저장 방지는 모두 결정적으로 확인되었다.

## 9. 수정 필요 항목

§7에서 지적한 두 가지 자유서술 문제(근거 없는 정상/비정상 판정, 원본에
없는 인과관계 서술)는 기술적 통과 항목이 아니며, 수정이 필요한 항목으로
기록한다.

## 10. 최종 판정

**수정 후 승인 가능**

정확한 결론은 다음과 같다: 수치·단위·근거 연결과 내부정보 차단은
결정적으로 검증할 수 있었으나, 정상·비정상 판정과 인과관계 같은 의미
수준의 임상적 해석은 의료진 검토가 여전히 필요했다.

다음은 이 검증으로 주장하지 않는다:
- 임상적 적절성 검증 완료
- 의료진 검증 완료
- 정상·비정상 판정 정확성 확인
- 의미 수준 오류 완전 차단
- qwen3:8b 성능 입증
- 의료적 정확성 보장
- KR Core V2 완전 준수

## 11. Human-in-the-Loop 필요성

- 결정적 Validator는 "구조화된 사실"(수치·단위·근거 연결)만 신뢰성
  있게 검증할 수 있다. "해석"(정상/비정상)과 "인과관계"는 자연어
  전체를 의미 수준에서 이해해야 판별 가능하며, 이는 결정적 규칙만으로
  보장할 수 없다.
- 따라서 승인 전 의료진 검토는 보조 절차가 아니라, 이 시스템 설계상
  필수불가결한 마지막 방어선이다. 이번 검증은 그 필요성을 실제 사례로
  보여준다.
- 모든 LLM/Mock 초안은 의료진이 승인하기 전까지 환자에게 공개되지
  않는 기존 워크플로우가, "장식적 안전장치"가 아니라 "실제로 필요한
  장치"임을 재확인했다.

## 12. 제한사항

- 1회 호출 결과이며, 모델의 출력은 결정적이지 않으므로 같은 입력에
  대해서도 매번 다른 표현이 나올 수 있다 — 이 결과를 일반화할 수 없다.
- 특정 모델(qwen3:8b, Q4_K_M)과 특정 Prompt 버전에 한정된 결과다.
- Diagnosis에 없는 새로운 진단을 의미 수준에서 완전히 차단하는 기능은
  이 검증의 범위가 아니며, 여전히 구현되어 있지 않다.
- 결정적 Validator만으로는 §7의 두 문제 유형을 탐지할 수 없다(별도
  분석 문서 참고 예정).

## 13. 후속 개선안

- (적용됨) `build_narrative_prompt()`의 `_INSTRUCTIONS`에 다음 세 가지
  안전 지시를 추가했다: VitalSign은 참고범위·판정 없이 중립적으로만
  서술, LabResult의 근거 있는 판정을 VitalSign에 일반화하지 않음,
  진단과 검사결과 사이의 인과관계를 추론하지 않음.
- (보류) 결정적 Validator에 판정어·인과접속사 탐지 패턴을 추가하는
  방안은 LabResult의 정당한 판정 표현 오탐, 한국어 복문에서의 지시대상
  구분 어려움 때문에 이번 Task에서는 채택하지 않았다 — Prompt 개선의
  실측 효과를 먼저 확인한 뒤 별도 Task로 재검토한다.
- (보류) 구조화 출력에 사실·해석·인과관계 claim 유형을 구분해 넣는
  근본적 재설계는 기존 Provider 계약·기존 보고서 호환성에 영향이 커서
  이번 Task 범위에서는 채택하지 않았다.

## 14. Prompt 개선 후 재검증 (2026-11-14)

**이 섹션은 위 §1~§13의 최초 검증 기록을 수정·삭제하지 않고 그 뒤에
추가한 것이다.**

### 14.1 재검증 목적과 조건

§13에서 "(적용됨)"으로 표시한 Prompt 안전 지시 3종(VitalSign 중립
서술, LabResult 판정의 VitalSign 일반화 금지, Diagnosis 인과관계
생성 금지)이 실제 qwen3:8b 출력에서도 §7의 두 문제(근거 없는
정상/비정상 판정, 원본에 없는 인과관계)를 줄이는지 **동일 조건 1회
재검증**으로 확인한다.

- 재검증 날짜/시각: 2026-11-14 (실제 호출 시도 07:45:35~07:46:35 UTC)
- 실행 환경: Windows 호스트에서 별도로 구동된 Ollama(`ollama serve`),
  Docker backend 컨테이너가 `host.docker.internal`로 호출 — 최초
  검증과 동일한 네트워크 경로
- Ollama version: `0.40.2`(최초 검증과 동일, `/api/version` read-only
  확인)
- 모델명: `qwen3:8b`, model ID `500a1f067a9f`
- Quantization: `Q4_K_M` — `/api/tags` 응답의 `details.quantization_level`
  필드에서 직접 확인(read-only metadata 조회, 추론 호출 아님)
- **동일 Encounter 사용 여부**: 예 — SYN-0001의 2026-03-10 내분비내과
  외래, 최초 검증과 동일
- **동일 Snapshot 재사용 여부**: **예, 리터럴하게 동일.** 최초 실제
  검증 당시 생성된(현재 `REJECTED` 상태로 보존된) 보고서의
  `content.emr_snapshot`을 DB에서 읍기 전용으로 그대로 읍어
  (`VitalSign 7종`/`LabResult 2건`/`Diagnosis 1건` 개수 일치 확인)
  `EmrSnapshot.model_validate()`로 복원한 뒤, **그 객체를 그대로**
  `build_narrative_prompt()`/`RealLLMProvider.generate()`에 전달했다
  — DB에서 다시 수집(`collect_report_data()`)하지 않았으므로 "같은
  값일 가능성"이 아니라 **같은 JSON 객체 자체**를 재사용했다.
- 새 합성 Patient/Encounter를 생성하지 않았고, VitalSign/LabResult/
  Diagnosis/seed를 전혀 수정하지 않았다(재검증 전후 해당 Encounter의
  `ClinicalReport` 행 수가 9건으로 동일함을 확인 — 새 DRAFT도 생성하지
  않았다).
- **실행 방법이 최초 검증과 다른 점**: 최초 검증은 Frontend→API→
  `generate_report_narrative()` 라우터 경로로 수행됐으나, 이번
  재검증은 **그 라우터를 거치지 않고** `RealLLMProvider.generate()`를
  Python에서 직접 호출했다. 이유: §14.2에서 발견한 것처럼 그 라우터는
  "narrative가 이미 있으면 Provider를 호출하지 않는다"는 멱등
  규칙이 있어, 기존 REJECTED 보고서에 재사용 시 실제 호출이 발생하지
  않기 때문이다. 직접 호출 방식은 DB에 어떤 행도 추가/수정하지 않고
  정확히 1회의 `generate()` 호출만 발생시키기 위한 선택이었다(Provider
  계약 자체는 수정하지 않았다 — `real_llm_provider.py`/
  `ollama_client.py` 코드를 전혀 변경하지 않고 기존 코드를 그대로
  import해서 호출만 했다).

### 14.2 실제 LLM 호출 횟수와 결과 — 호출 실패(timeout)

**`provider.generate(snapshot)`를 정확히 1회 호출했다.** 그 결과:

```
CALL_TIME_UTC_BEFORE= 2026-11-14T07:45:35Z
CALL_TIME_UTC_AFTER=  2026-11-14T07:46:35Z  (약 60초 경과)
PROVIDER_SUCCESS=False
ERROR_TYPE= NarrativeProviderError
ERROR= NarrativeProviderError('LLM_REQUEST_FAILED')
```

**투명성 공개(중요)**: 호출 직후 `app/services/narrative_providers/
ollama_client.py`를 다시 읍어보니, `OllamaHttpClient.complete()`에
**timeout/5xx 오류에 대해 최초 1회 + 자동 재시도 최대 1회(`_MAX_ATTEMPTS
= 2`)를 수행하는 기존 로직이 이미 있었다.** 소요 시간(~60초 ≈
timeout_seconds(30) × 2 + 재시도 지연(0.5))과 정확히 일치해, **이번
`generate()` 1회 호출 내부에서 실제로는 Ollama에 최대 2회의 HTTP
`/api/chat` 요청이 전송됐을 가능성이 있다.** 이는 재검증 작업을
지시한 쪽에서 요청한 "정확히 1회 호출"을 오케스트레이션 수준에서는
정확히 지켰지만(의도적으로 `generate()`를 두 번 부르지 않았다), **그
아래 계층의 기존 재시도 로직까지는 통제하지 못했다는 뜻이다.** 이
사실을 숨기지 않고 그대로 기록한다. 추가 수동 재시도는 하지 않았다.

**서버 측 로그 조사(읍기 전용)**: Ollama의 `server.log`를 확인했으나
`OLLAMA_DEBUG_LOG_REQUESTS:false` 설정 때문에 개별 요청 로그가 남지
않았고, 호출 시각대(16:44~16:47 KST)에 어떤 로그 줄도 없었다. GPU
메모리는 확인 시점에 약 6.7GB/16.3GB 사용 중이었으나(`qwen3:8b` 로드와
일치하는 크기), 이것이 **이번 요청으로 로드된 것인지, 그 이전부터
로드돼 있던 것인지는 서버 로그로 확정할 수 없었다** — 추측하지 않고
**"확인 불가"**로 기록한다.

### 14.3 Provider 결과 보존 및 분석

- Provider 성공/실패: **실패**
- Parsing 결과: 해당 없음(응답 자체가 없음)
- Narrative 생성 여부: **생성되지 않음**
- 이 실패를 "모델이 응답을 거부했다"거나 "검증에 실패했다"로
  과장하지 않는다 — **원인은 timeout이며, 모델이 실제로 틀린 내용을
  반환한 것이 아니다.**

### 14.4 자동 Validator 실행 결과

**실행 불가.** `validate_narrative_provider_result()`는
`NarrativeProviderResult` 객체를 입력으로 받는데, 이번 호출은 그
객체 자체가 생성되지 않았으므로(예외로 종료) Validator를 실행할
대상이 없다. narrative_validation.py는 전혀 수정하지 않았다.

### 14.5 VitalSign 수동 검토 / 14.6 LabResult·VitalSign 규칙 분리 /
### 14.7 Diagnosis 인과관계 검토

**해당 없음(narrative가 생성되지 않음).** §7~§9에서 지적한 문제가
"개선되었는지"를 이번 1회 시도로는 **확인하지 못했다.**

### 14.8 기존 안전장치 회귀 검토

narrative가 없으므로 회귀 여부를 narrative 내용으로는 확인할 수
없다. 다만 다음은 확인했다: 이번 시도로 **DB에 어떤 새 행도 추가되지
않았고(ClinicalReport 9건 그대로), 어떤 기존 행도 수정되지 않았으며,
`backend/.env`의 `NARRATIVE_PROVIDER`도 계속 `mock`으로 남아 있었다**
(한 번도 바꾸지 않았으므로). MRN/환자 이름/생년월일/
`source_record_ids` 전문/내부 Evidence Tag — 이번 재검증 과정에서
어디에도 출력하지 않았다.

### 14.9 최초 검증과 비교

| 항목 | 최초 검증(§1~§13) | 이번 재검증 |
|---|---|---|
| Patient/Encounter | SYN-0001 / 2026-03-10 | 동일 |
| Snapshot | 그 시점에 새로 수집 | **최초 검증이 만든 동일 Snapshot 객체를 그대로 재사용** |
| 모델 | qwen3:8b(Q4_K_M) | 동일 |
| 결과 | narrative 생성 성공 | **호출 실패(timeout), narrative 없음** |
| VitalSign 임의 판정 | 발생("정상 범위에 속합니다") | 평가 불가(결과 없음) |
| Diagnosis 인과관계 | 발생("이에 따라 ... 진단되었습니다") | 평가 불가(결과 없음) |
| Validator | PASS(사실 수준) | 실행 불가 |

**최초 REJECTED의 원인(의미 수준 판정/인과관계)이 이번에도
재현됐는지는 판단할 수 없다** — 비교할 narrative 자체가 없기
때문이다. 이번 실패는 §7~§9와 **다른 종류의 문제**(인프라/timeout)다.

### 14.10 최종 판정

**PASS/PARTIAL/FAIL 중 어느 것도 선택하지 않는다.** 세 판정 모두
"narrative가 생성되었다"는 전제 위에서만 의미가 있는데, 이번 1회
시도는 그 전제 자체가 성립하지 않았다. 정직한 표현은:

> **"이번 동일 조건 1회 재검증은 모델 호출이 timeout으로 실패해
> narrative를 생성하지 못했다. 따라서 Prompt 개선이 §7~§9의 문제를
> 줄였는지는 이번 시도로 확인되지 않았다(검증 미완료)."**

다음은 이 재검증으로 주장하지 않는다:
- Prompt 개선이 효과가 있었다/없었다
- qwen3:8b가 이 조건에서 안정적으로 응답한다/못한다
- timeout 설정(30초)이 부족하다/충분하다(1회 샘플로는 일반화 불가)

### 14.11 Human-in-the-Loop 필요성

이번 결과는 §11의 결론을 바꾸지 않는다 — 오히려 "LLM 경로 자체가
완전히 결정적이지 않다"(timeout 포함)는 또 다른 이유로, 의료진 검토
전 환자 비공개 원칙이 필요하다는 기존 결론을 보강한다.

### 14.12 남은 제한사항(갱신)

- Prompt 개선의 실제 효과는 **여전히 미확인 상태**다 — 재시도는
  이번 턴에서 금지되었으므로, 효과 확인은 **별도의 승인된 시도**가
  필요하다.
- `OllamaHttpClient`에 기존부터 내장된 재시도 로직(`_MAX_ATTEMPTS=2`)
  때문에, 앞으로 "정확히 1회 호출"을 요구하는 검증을 설계할 때는
  이 내장 재시도까지 고려해야 한다(이번에 새로 발견한 사실).
  `ollama_client.py`는 이번 턴에서 수정하지 않았다.
- 30초 timeout이 이 하드웨어·이 Prompt 길이·이 JSON Schema
  (구조화 출력 강제 디코딩)에서 충분한지는 확인되지 않았다.
- GPU 메모리에 모델이 로드되어 있었는지(이번 요청 때문인지 이전부터인지)는
  "확인 불가"로 남긴다 — 추측하지 않았다.

## 15. 최종 1회 재검증 — production-equivalent 직접 HTTP 호출 (2026-11-14, §14와 별개)

**이 섹션은 §1~§14의 기록을 수정·삭제하지 않고 그 뒤에 추가한 것이다.**
§14(Provider 경유 호출, timeout)가 "정확히 1회 호출"을 보장하지 못한
문제(`OllamaHttpClient`의 내장 재시도 `_MAX_ATTEMPTS=2`)를 해결하기
위해, 이번에는 production `OllamaHttpClient`를 거치지 않고 **동일한
요청 내용을 production 코드로 구성한 뒤, 재시도 로직이 없는 별도
HTTP 클라이언트(curl)로 정확히 1회만 전송**했다.

### 15.1 실행 환경

- 실행 날짜/시각: 2026-11-14, 08:14:16~08:14:26 UTC
- Ollama: `0.40.2`, 모델 `qwen3:8b`, model ID `500a1f067a9f`, quantization `Q4_K_M`
- **호출 직전 `GET /api/ps` 결과**: `{"models": []}` — **로드된 모델 없음(cold 상태)**을 확인했다. 이 cold 상태를 해소하기 위한 별도의 warm-up 생성 호출은 하지 않았고, cold 상태 그대로 최종 검증을 수행했다.

### 15.2 production request와 검증 request의 동등성

| 구성요소 | production(`OllamaHttpClient.complete()`) | 이번 검증 요청 | 동일 여부 |
|---|---|---|---|
| Prompt 본문 | `build_narrative_prompt(snapshot)`(동일 함수, 동일 Snapshot) | 동일 함수를 read-only로 호출해 그대로 재사용 | **동일(코드 재사용, 재구현 아님)** |
| `model` | `qwen3:8b` | `qwen3:8b` | 동일 |
| `stream` | `False` | `False` | 동일 |
| `think` | `False` | `False` | 동일 |
| `format` | `LlmStructuredOutput.model_json_schema()` | 동일 함수를 read-only로 호출해 그대로 재사용 | **동일** |
| `options` | `{"temperature": 0, "num_predict": max_output_tokens}` | `{"temperature": 0, "num_predict": 1000}`(production 기본값과 동일) | 동일 |
| 엔드포인트 경로 | `{base_url}/api/chat` | `http://127.0.0.1:11434/api/chat` | 동일 경로, **base_url 문자열만 다름**(§15.3) |
| 재시도 | `_MAX_ATTEMPTS=2`(timeout/5xx 자동 재시도) | **없음(단일 시도, 재시도 로직 자체를 코드에 두지 않음)** | **의도적으로 다름** |
| 읍기 timeout | `30`초(production 기본값) | `120`초(검증 전용, 로컬 변수) | **의도적으로 다름** |

**동일하지 않은 두 항목(재시도, timeout)은 결과 타당성에 영향을 주지 않는다** — 둘 다 "모델이 실제로 무엇을 반환하는가"가 아니라 "클라이언트가 얼마나 기다리고 몇 번 시도하는가"에만 관여하는 전송 계층 설정이기 때문이다. Prompt·모델·생성 옵션·스키마는 전부 production 코드를 그대로 재사용해 동일성을 확보했으므로, **검증을 중단할 정도의 차이는 없다고 판단해 호출을 진행했다.**

### 15.3 base_url 차이에 대한 설명

production은 Docker backend 컨테이너 내부에서 `http://host.docker.internal:11434`로 호출하고, 이번 검증은 Windows 호스트에서 직접 `http://127.0.0.1:11434`로 호출했다 — **둘 다 같은 물리적 Ollama 서버 프로세스**를 가리키며(포트 11434, 같은 머신), 호스트명 해석 경로만 다르다. 이 차이가 모델의 응답 내용에 영향을 줄 이유는 없다.

### 15.4 실제 inference HTTP 요청

- `actual_inference_http_requests = 1`(curl 단일 POST, 재시도 없음, retry transport 없음)
- `connect-timeout 10`, `--max-time 120`(검증 전용 로컬 설정 — production `llm_timeout_seconds=30`/`_MAX_ATTEMPTS=2`는 전혀 수정하지 않았다)
- 요청: `POST http://127.0.0.1:11434/api/chat`
- **응답: HTTP 200**, 클라이언트 측 측정 왕복 시간 **9.916초**
- Ollama 응답 envelope의 서버 측 측정값: `total_duration=9.898초`, `load_duration=2.642초`, `prompt_eval_count=1261`, `eval_count=398`
- 실패/timeout/5xx 없음 → **추가 POST를 전혀 수행하지 않았다.**

### 15.5 Patient/Encounter/Snapshot 동일성

SYN-0001 / 2026-03-10 내분비내과 외래 — §1·§14와 동일. Snapshot은 §14와 **같은 DB 행(최초 REJECTED 보고서)에서 다시 읍기 전용으로 추출**했으며(VitalSign 7/LabResult 2/Diagnosis 1 개수 일치), 재검증 전후 해당 Encounter의 ClinicalReport 행 수가 **9건으로 변화 없음**을 확인했다(새 DRAFT 생성 없음, DB write 없음).

### 15.6 Provider 결과 생성 성공 여부 / parsing·schema 결과

**성공.** 반환된 `message.content`는 `LlmStructuredOutput.model_validate_json()`(production 스키마, 수정 없음)을 **그대로 통과**했다.

```json
{
  "narrative": "2026년 3월 10일 09시에 내분비내과 외래를 방문한 환자는 2형 당뇨병이 신규로 진단되었습니다. 혈당 검사에서 HbA1c는 7.2%로, 참고범위 4.0-6.0%를 벗어난 것으로 나타났습니다. 공복혈당은 130.0mg/dL로, 참고범위 70.0-100.0mg/dL를 초과한 것으로 확인되었습니다. 환자의 혈압은 120.000/80.000mmHg로 측정되었으며, 키는 170.000cm, 체중은 65.000kg이었습니다. 체온은 36.500℃, 맥박은 72.000회/분, 호흡수는 16.000회/분, 산소포화도는 98.000%로 측정되었습니다. 알레르기로는 펜실린에 대해 두드러기 반응이 있는 것으로 기록되어 있습니다. 처방으로는 메트포르민 500mg, 펜실린 V 500mg, Task10VerifyNonConflictMedX 1정이 포함되었습니다.",
  "evidence_tags": ["E1","D1","L1","L2","V1","V2","V3","V4","V5","V6","V7","A1","P1","P2","P3"]
}
```

원본 response와 parsing 결과를 그대로 구분해 보존했고(개인정보·내부 숫자 ID는 위에 없음 — MRN/이름/생년월일/`vital_sign:{id}` 등 원문 식별자는 전혀 포함되지 않음), 어떤 텍스트도 임의로 수정·보정하지 않았다.

### 15.7 Validator 결과

`_resolve_evidence_tags()`(production, 수정 없음)로 15개 태그 전부 정상 해석(`E1,D1,L1,L2,V1~V7,A1,P1,P2,P3` → `encounter:1, diagnosis:1, lab_result:1/2, vital_sign:2~8, allergy:1, prescription:1/5/6`). `validate_narrative_provider_result()`(production, 수정 없음) 실행 결과: **`ok=True, reason=None`(PASS)**.

**중요한 한계 공개**: 이번 응답은 `mentioned_measurements`/`mentioned_vital_signs`를 **둘 다 빈 배열로 반환**했다(Prompt가 `mentioned_measurements`를 채우라고는 지시하지만 `mentioned_vital_signs`를 채우라는 지시는 없다 — 이번에 새로 발견한 기존 Prompt의 공백, §15.16 참고). 그 결과 Validator의 **수치별 교차검증(`_measurement_exists_in_snapshot`/`_vital_sign_mentioned_exists_in_snapshot`)은 비교 대상이 없어 사실상 실행되지 않았다** — `cited_record_ids` 부분집합 검사와 금지어/태그 누출 검사만 실제로 수행됐다. **"Validator PASS"를 §6(최초 검증)과 같은 수준의 수치 교차검증으로 과장하지 않는다.** 이 공백을 보완하기 위해 아래 §15.8에서 모든 수치를 수동으로 전수 대조했다.

**Validator PASS는 임상적 안전성 검증 완료를 의미하지 않는다.**

### 15.8 VitalSign 의미판정 수동 검토

narrative의 VitalSign 문장("환자의 혈압은 120.000/80.000mmHg로 측정되었으며, 키는 170.000cm, 체중은 65.000kg이었습니다. 체온은 36.500℃, 맥박은 72.000회/분, 호흡수는 16.000회/분, 산소포화도는 98.000%로 측정되었습니다.")을 전부 확인했다.

- 금지 단어(정상/비정상/높음/낮음/안정적/양호): **전혀 없음**
- 의미상 동등 판정("걱정할 수준 아님", "문제 없는 수치", "위험하지 않음", "건강한 범위", "위험한 수준" 등): **전혀 없음**
- 전부 "측정되었다"/"이었다"는 순수 사실 서술만 사용함 — **§7(최초 검증)의 "정상 범위에 속합니다"/"정상 범위에 해당합니다" 문제가 재현되지 않았다.**

**수동 수치 대조표(원본 Snapshot ↔ narrative)**:

| 항목 | Snapshot | narrative | 일치 |
|---|---|---|---|
| 혈압 | 120.000/80.000 mmHg | 120.000/80.000mmHg | 일치 |
| 키 | 170.000 cm | 170.000cm | 일치 |
| 체중 | 65.000 kg | 65.000kg | 일치 |
| 체온 | 36.500 Cel | 36.500℃ | 일치(단위 표기를 Cel→℃로 모델이 스스로 변환 — Prompt가 이 변환을 명시적으로 지시하지는 않았다, §15.16) |
| 맥박 | 72.000 /min | 72.000회/분 | 일치(표기 변환, 값 자체는 동일) |
| 호흡수 | 16.000 /min | 16.000회/분 | 일치 |
| 산소포화도 | 98.000 % | 98.000% | 일치 |

7종 전부 **수치·단위 일치, 변조 없음.**

### 15.9 LabResult/VitalSign 구분 결과

LabResult 문장("HbA1c는 7.2%로, 참고범위 4.0-6.0%를 벗어난 것으로 나타났습니다", "공복혈당은 130.0mg/dL로, 참고범위 70.0-100.0mg/dL를 초과한 것으로 확인되었습니다")은 Snapshot에 실제로 존재하는 `reference_low`/`reference_high`(HbA1c 4.0-6.0, 공복혈당 70.0-100.0)를 **그대로 인용**하며 그 범위 내에서만 "벗어난"/"초과한"이라고 서술했다 — 근거 있는 판정이다. 이 판정 논리가 VitalSign 문장으로 전이된 흔적은 **없다**(§15.8 참고, VitalSign 문장에는 참고범위·판정 언급이 전혀 없음). **LabResult/VitalSign 규칙 분리가 그대로 유지되었다.**

### 15.10 Diagnosis 인과관계 검토

narrative의 진단 문장은 "...환자는 2형 당뇨병이 신규로 진단되었습니다."로, 검사결과 문장들보다 **앞에** 독립적으로 등장하며, "이에 따라"/"그 결과"/"때문에 진단되었습니다"/"따라서 진단되었습니다"/"검사 결과로 진단되었습니다"/"~로 인해 진단되었습니다" 중 **어느 표현도, 그와 동등한 의미의 어떤 문장도 전혀 사용되지 않았다.** 검사결과와 진단은 각각 독립된 사실로만 서술되었다 — **§7의 "이에 따라 2형 당뇨병이 신규 진단되었습니다" 문제가 재현되지 않았다.** Snapshot에 없는 새로운 진단도 생성되지 않았다(Diagnosis 레코드의 "2형 당뇨병"과 정확히 일치).

### 15.11 기존 안전장치 회귀 결과

전부 확인됨 — 새 진단 없음, 치료 권고 없음, 약물 추가·변경·중단 지시 없음(처방을 "포함되었습니다"로만 사실 서술), 재검사 지시 없음, 위험도 확정 없음, 예후 예측 없음, Snapshot에 없는 새 수치 없음, 수치·단위 변조 없음(§15.8), MRN/환자이름/생년월일 노출 없음, `source_record_ids` 전문(`vital_sign:2` 등) 노출 없음, narrative 본문에 V/E/D/L/P/A 태그 텍스트 노출 없음(태그는 별도 JSON 필드에만 존재), 기타 내부 identifier 노출 없음. **회귀 없음.**

### 15.12 최초 REJECTED(§1~§13)와 비교

| 항목 | 최초(§1~§13) | 이번(§15) |
|---|---|---|
| VitalSign 임의 판정 | 발생("정상 범위에 속합니다" 등) | **발생하지 않음** |
| Diagnosis 인과관계 | 발생("이에 따라 ... 진단되었습니다") | **발생하지 않음** |
| 수치·단위 정확성 | 일치 | 일치 |
| 근거 연결(evidence_tags→cited_record_ids) | 성공 | 성공(15개 태그 전부) |
| Validator | PASS(단, 수치별 교차검증 실제 수행) | PASS(단, 수치별 교차검증은 **빈 자기보고로 미실행** — §15.7) |

**최초 REJECTED의 원인(§7의 두 문제)이 이번에는 재현되지 않았다.**

### 15.13 §14(timeout 재검증)와 비교

§14는 `provider.generate()`를 경유해 timeout으로 완전히 실패했고(narrative 자체가 없었음), 이번은 production 코드와 동일한 Prompt/스키마/옵션을 재시도 없는 단일 HTTP 호출로 보내 **9.9초 만에 성공**했다. 두 시도의 유일한 체계적 차이는 전송 계층(재시도 유무, timeout 길이)이었다는 점에서, **§14의 실패 원인이 "모델이 이 Prompt에 응답할 수 없다"가 아니라 전송/타이밍 쪽 문제였을 가능성에 부합하는 결과**다(다만 §14 자체의 정확한 원인은 여전히 로그로 확정되지 않았다 — 이전 조사 보고 그대로).

### 15.14 최종 판정: **PASS**

PASS 조건 재확인:
- `actual_inference_http_requests = 1` 충족
- 정상적인 Narrative 결과 확보 충족
- 기존 VitalSign 판정 문제 재현되지 않음 충족
- 기존 Diagnosis 인과관계 문제 재현되지 않음 충족
- 중대한 새로운 근거 위반 없음 충족(수동 전수 대조로 확인)
- 기존 안전장치 회귀 없음 충족

**PASS의 의미는 정확히 다음으로 제한한다**: "동일한 합성 Encounter와 Snapshot을 사용한 이번 단일 실제 qwen3:8b 재검증에서 기존에 관찰된 실패 유형(근거 없는 정상/비정상 판정, 원본에 없는 인과관계)이 재현되지 않았다." 다음은 주장하지 않는다: 임상적 안전성 검증 완료, 의료적 정확성 보장, hallucination 제거 완료, 임상 사용 가능 확인, 의료진 검토 불필요.

### 15.15 Human-in-the-Loop 필요성(갱신)

이번 PASS는 "결정적 Validator + Prompt 개선"의 조합이 **이번 1회 샘플에서는** 효과가 있었음을 보여주지만, (a) 1회 샘플이라 일반화할 수 없고, (b) Validator의 수치 교차검증이 이번에는 모델의 자기보고 누락으로 실행되지 않았다는 구조적 한계가 그대로 남아 있다(§15.7). 승인 전 의료진 검토가 필요하다는 기존 결론(§11)은 바뀌지 않는다 — 오히려 "같은 Prompt로도 모델이 매번 같은 필드를 채우지는 않는다"는 비결정성이 추가로 확인되어, 자동화만으로 완결할 수 없다는 근거가 보강된다.

### 15.16 남은 제한사항(이번 재검증 기준)

- **1회 성공이 "항상 성공"을 보장하지 않는다** — §14는 같은 Prompt·같은 Snapshot으로 timeout됐고, 이번은 성공했다. 재현성 자체가 낮다(모델/하드웨어 특성상 예상되는 변동).
- Prompt는 `mentioned_measurements`를 채우라고 지시하지만 **`mentioned_vital_signs`를 채우라는 지시가 없다** — 이번 응답이 그 필드를 비워 Validator의 수치 교차검증이 실행되지 않은 직접적 원인이다. **(설계 제안만, 코드 수정 안 함)**: `_INSTRUCTIONS`에 "narrative에서 언급한 모든 VitalSign 값도 mentioned_vital_signs에 포함하라"는 문장을 추가하면 이 공백을 메울 수 있을 것으로 보인다 — 단, 이번 턴에서는 **구현하지 않았다.**
- 체온/맥박/호흡수의 단위 표기(Cel→℃, /min→회/분)를 모델이 스스로 변환한 것은 이번엔 정확했지만, Prompt가 이를 명시적으로 지시하지 않으므로 **다음 호출에서도 항상 정확할 것이라는 보장은 없다.**
- 여전히 Diagnosis의 의미 수준 완전 차단(새 진단 생성 방지)은 결정적으로 보장되지 않는다 — 이번 샘플에서 우연히 문제가 없었을 뿐이다.
