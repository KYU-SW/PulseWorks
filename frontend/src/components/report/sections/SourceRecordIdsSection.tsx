import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

export default function SourceRecordIdsSection({
  snapshot,
  title,
  emptyBehavior,
}: SectionComponentProps) {
  const hasData = snapshot.source_record_ids.length > 0;
  return (
    <SectionShell id="source_record_ids" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      <ul>
        {snapshot.source_record_ids.map((recordId) => (
          <li key={recordId}>{recordId}</li>
        ))}
      </ul>
    </SectionShell>
  );
}
