import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

// 환자 기본정보는 보고서에 항상 존재하는 정보이므로 항상 표시한다.
export default function PatientInfoSection({ snapshot, title, emptyBehavior }: SectionComponentProps) {
  const { patient } = snapshot;
  return (
    <SectionShell id="patient_info" title={title} hasData={true} emptyBehavior={emptyBehavior}>
      <p>이름: {patient.name}</p>
      <p>MRN: {patient.mrn}</p>
      <p>생년월일: {patient.birth_date}</p>
    </SectionShell>
  );
}
