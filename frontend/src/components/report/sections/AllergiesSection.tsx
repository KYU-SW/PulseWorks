import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

export default function AllergiesSection({ snapshot, title, emptyBehavior }: SectionComponentProps) {
  const hasData = snapshot.allergies.length > 0;
  return (
    <SectionShell
      id="allergies"
      title={title}
      hasData={hasData}
      emptyBehavior={emptyBehavior}
      emptyText="등록된 합성 알레르기 정보가 없습니다."
    >
      <ul>
        {snapshot.allergies.map((allergy) => (
          <li key={allergy.id}>
            {allergy.substance} — {allergy.reaction} (심각도: {allergy.severity})
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}
