import { PatientVitalSign } from "../../api/patientReports";
import { formatVitalSignValue, VitalType } from "../vitalSign/formatVitalSign";
import Card from "../ui/Card";

// Task F4-B: app/routers/encounters.py의 _VITAL_TYPE_LABELS와 동일한 값 -
// 이 프로젝트의 기존 패턴대로 각 파일이 독립적으로 라벨을 선언한다.
const VITAL_TYPE_LABELS: Record<string, string> = {
  BLOOD_PRESSURE: "혈압",
  BODY_HEIGHT: "키",
  BODY_WEIGHT: "체중",
  BODY_TEMPERATURE: "체온",
  HEART_RATE: "맥박",
  RESPIRATORY_RATE: "호흡수",
  PULSE_OXIMETRY: "산소포화도",
};

export default function PatientVitalSignsList({ vitalSigns }: { vitalSigns: PatientVitalSign[] }) {
  if (vitalSigns.length === 0) return null;

  return (
    <ul className="page-stack">
      {vitalSigns.map((vital, index) => (
        <li key={`${vital.vital_type}-${index}`}>
          <Card>
            <p>
              {VITAL_TYPE_LABELS[vital.vital_type] ?? "활력징후"}:{" "}
              {formatVitalSignValue(
                vital.vital_type as VitalType,
                vital.value,
                vital.value_secondary,
                vital.unit
              )}
            </p>
          </Card>
        </li>
      ))}
    </ul>
  );
}
