import { formatDateTime } from "../../labTrend/LabTrendPresentation";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

// preview_text는 이미 Task 8/12에서 300자로 잘려 저장된 값이다 — 여기서
// 다시 자르거나 원문을 따로 가져오지 않는다.
export default function ClinicalNotesSection({
  snapshot,
  title,
  emptyBehavior,
}: SectionComponentProps) {
  const hasData = snapshot.clinical_notes.length > 0;
  return (
    <SectionShell id="clinical_notes" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      <ul>
        {snapshot.clinical_notes.map((note) => (
          <li key={note.id}>
            {note.preview_text} ({formatDateTime(note.created_at)})
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}
