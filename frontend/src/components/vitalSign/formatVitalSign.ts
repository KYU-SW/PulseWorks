// Task F4-A: Backend는 정밀도를 보존하기 위해 value/value_secondary를
// Decimal 문자열 그대로 보낸다(예: "72.000", "36.500") — 여기서만 화면
//표시용으로 자릿수를 줄인다. 원본 문자열(API 응답)은 건드리지 않는다
// (이 함수는 새 문자열을 만들어 반환할 뿐이다).
//
// KR Core IG v1.0.2 StructureDefinition에서 확인한 7종(docs/standards/
// kr-cdi-kr-core-mapping.md §3)의 화면 표시 자릿수:
// - 혈압·맥박·호흡수·산소포화도: 정수
// - 키·체중·체온: 소수점 최대 1자리
// - BMI: 소수점 1자리(Backend가 이미 반올림해서 보내므로 그대로 표시)

export type VitalType =
  | "BLOOD_PRESSURE"
  | "BODY_HEIGHT"
  | "BODY_WEIGHT"
  | "BODY_TEMPERATURE"
  | "HEART_RATE"
  | "RESPIRATORY_RATE"
  | "PULSE_OXIMETRY";

const _INTEGER_TYPES: ReadonlySet<VitalType> = new Set([
  "BLOOD_PRESSURE",
  "HEART_RATE",
  "RESPIRATORY_RATE",
  "PULSE_OXIMETRY",
]);

// canonical 단위(저장값, ASCII) -> 화면 표시 라벨. 체온만 "Cel"을
// 사람이 읽기 쉬운 "℃"로 바꾼다 — 저장값 자체는 바꾸지 않는다.
const _DISPLAY_UNIT_LABELS: Record<string, string> = {
  Cel: "℃",
};

function _roundForDisplay(rawValue: string, vitalType: VitalType): string {
  const parsed = Number(rawValue);
  if (!Number.isFinite(parsed)) {
    return rawValue; // 예상치 못한 형식이면 원본을 그대로 보여준다(추측 금지).
  }
  const decimals = _INTEGER_TYPES.has(vitalType) ? 0 : 1;
  return parsed.toFixed(decimals);
}

export function formatVitalSignDisplayUnit(canonicalUnit: string): string {
  return _DISPLAY_UNIT_LABELS[canonicalUnit] ?? canonicalUnit;
}

// ℃·%는 한글 표기 관례상 숫자에 붙여 쓰고, 그 외(mmHg/cm/kg//min)는
// 띄어 쓴다 — 기존 LabResult 화면 표시(예: "7.2%")와도 맞춘다.
const _NO_SPACE_UNITS: ReadonlySet<string> = new Set(["℃", "%"]);

export function formatVitalSignValue(
  vitalType: VitalType,
  value: string,
  valueSecondary: string | null,
  unit: string
): string {
  const displayUnit = formatVitalSignDisplayUnit(unit);
  const separator = _NO_SPACE_UNITS.has(displayUnit) ? "" : " ";
  if (vitalType === "BLOOD_PRESSURE" && valueSecondary !== null) {
    const systolic = _roundForDisplay(value, vitalType);
    const diastolic = _roundForDisplay(valueSecondary, vitalType);
    return `${systolic}/${diastolic}${separator}${displayUnit}`;
  }
  return `${_roundForDisplay(value, vitalType)}${separator}${displayUnit}`;
}
