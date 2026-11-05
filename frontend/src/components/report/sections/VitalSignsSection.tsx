import { formatVitalSignValue, VitalType } from "../../vitalSign/formatVitalSign";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

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

export default function VitalSignsSection({ snapshot, title, emptyBehavior }: SectionComponentProps) {
  const hasData = snapshot.vital_signs.length > 0;
  return (
    <SectionShell
      id="vital_signs"
      title={title}
      hasData={hasData}
      emptyBehavior={emptyBehavior}
      emptyText="측정된 활력징후 기록이 없습니다."
    >
      <ul>
        {snapshot.vital_signs.map((vital) => (
          <li key={vital.id}>
            {VITAL_TYPE_LABELS[vital.vital_type] ?? vital.vital_type}:{" "}
            {formatVitalSignValue(
              vital.vital_type as VitalType,
              vital.value,
              vital.value_secondary,
              vital.unit
            )}{" "}
            ({vital.measured_at})
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}
