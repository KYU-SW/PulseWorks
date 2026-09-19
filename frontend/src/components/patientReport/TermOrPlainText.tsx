import { findMedicalTerm } from "../../medicalTerms/findMedicalTerm";
import MedicalTermButton from "../medicalTerm/MedicalTermButton";

// Task 18의 findMedicalTerm()으로 정확 매칭되는 텍스트만 클릭 가능한
// 용어 버튼으로 바꾸고, 그 외에는 평문 그대로 보여준다. 자유 서술형
// 문장(narrative/patient_guidance/evidence)에는 쓰지 않는다 — 그 안에서
// 자동으로 용어를 찾지 않는다는 정책 때문에, 이 컴포넌트는 오직
// "그 값 자체가 하나의 용어인" 필드(검사명, 진료 형태 등)에만 쓴다.
export default function TermOrPlainText({ text }: { text: string }) {
  const term = findMedicalTerm(text);
  if (!term) return <>{text}</>;
  return <MedicalTermButton term={term}>{text}</MedicalTermButton>;
}
