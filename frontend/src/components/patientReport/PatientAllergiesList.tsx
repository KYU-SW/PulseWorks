import { PatientAllergy } from "../../api/patientReports";

const SEVERITY_LABELS: Record<string, string> = {
  MILD: "경미",
  MODERATE: "중간",
  SEVERE: "심함",
  UNKNOWN: "기록 없음",
};

// 등록되지 않은/알 수 없는 severity 값도 원문을 그대로 노출하지 않고
// 안전한 일반 표현으로 대체한다 - 화면에 처리되지 않은 내부 코드
// 문자열이 그대로 새어나가지 않게 한다.
function severityLabel(severity: string): string {
  return SEVERITY_LABELS[severity] ?? "확인 필요";
}

export default function PatientAllergiesList({ allergies }: { allergies: PatientAllergy[] }) {
  if (allergies.length === 0) return null;

  return (
    <ul>
      {allergies.map((allergy, index) => (
        <li key={`${allergy.substance}-${index}`}>
          <p>등록된 알레르기 정보</p>
          <ul>
            <li>물질: {allergy.substance}</li>
            <li>기록된 반응: {allergy.reaction}</li>
            <li>기록된 정도: {severityLabel(allergy.severity)}</li>
          </ul>
        </li>
      ))}
    </ul>
  );
}
