import { formatDateTime } from "../../labTrend/LabTrendPresentation";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

export default function DiagnosesSection({ snapshot, title, emptyBehavior }: SectionComponentProps) {
  const hasData = snapshot.diagnoses.length > 0;
  return (
    <SectionShell id="diagnoses" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      <ul>
        {snapshot.diagnoses.map((diagnosis) => (
          <li key={diagnosis.id}>
            {diagnosis.description} ({diagnosis.code}) — {formatDateTime(diagnosis.diagnosed_at)}
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}
