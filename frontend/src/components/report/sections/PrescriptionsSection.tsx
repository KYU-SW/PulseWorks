import { formatDateTime } from "../../labTrend/LabTrendPresentation";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

export default function PrescriptionsSection({
  snapshot,
  title,
  emptyBehavior,
}: SectionComponentProps) {
  const hasData = snapshot.prescriptions.length > 0;
  return (
    <SectionShell id="prescriptions" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      <ul>
        {snapshot.prescriptions.map((prescription) => (
          <li key={prescription.id}>
            {prescription.medication_name} — {prescription.dosage} —{" "}
            {formatDateTime(prescription.prescribed_at)}
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}
