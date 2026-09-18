import { formatDateTime } from "../../labTrend/LabTrendPresentation";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

const DEPARTMENT_LABELS: Record<string, string> = {
  ENDOCRINOLOGY: "내분비내과",
  ORTHOPEDICS: "정형외과",
  EMERGENCY_MEDICINE: "응급의학과",
};

const ENCOUNTER_TYPE_LABELS: Record<string, string> = {
  OUTPATIENT: "외래",
  INPATIENT: "입원",
  EMERGENCY: "응급",
};

// 이번 Task는 SINGLE_ENCOUNTER 보고서만 다루지만, snapshot.encounters를
// 그대로 나열해 향후 기간/전체이력 보고서에서 여러 건이 와도 그대로
// 동작한다. 이 보고서가 어떤 방문을 다루는지는 항상 존재하는 정보이므로
// 항상 표시한다.
export default function SelectedEncounterSection({
  snapshot,
  title,
  emptyBehavior,
}: SectionComponentProps) {
  return (
    <SectionShell id="selected_encounter" title={title} hasData={true} emptyBehavior={emptyBehavior}>
      <ul>
        {snapshot.encounters.map((encounter) => (
          <li key={encounter.id}>
            {DEPARTMENT_LABELS[encounter.department] ?? encounter.department}{" "}
            {ENCOUNTER_TYPE_LABELS[encounter.encounter_type] ?? encounter.encounter_type} —{" "}
            {formatDateTime(encounter.start_time)}
            {encounter.end_time ? ` ~ ${formatDateTime(encounter.end_time)}` : ""}
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}
