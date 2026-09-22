import { useRef, useState } from "react";
import { MedicalTerm } from "../../medicalTerms/types";
import MedicalTermDialog from "./MedicalTermDialog";

interface MedicalTermButtonProps {
  term: MedicalTerm;
  children: React.ReactNode;
}

// 실제 페이지에는 아직 연결하지 않는 독립 재사용 부품이다 (Task 19에서
// 환자용 보고서에 연결한다). 밑줄과 ⓘ 아이콘으로 색상과 무관하게
// 클릭 가능함을 알린다 — hover만으로는 열리지 않고 클릭/Enter/Space로만
// 열린다(실제 button 요소의 기본 동작).
export default function MedicalTermButton({ term, children }: MedicalTermButtonProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <>
      <button
        type="button"
        className="ui-term-trigger"
        ref={triggerRef}
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        <span style={{ textDecoration: "underline" }}>{children}</span>
        <span aria-hidden="true"> ⓘ</span>
      </button>
      {open && (
        <MedicalTermDialog term={term} onClosed={() => setOpen(false)} returnFocusRef={triggerRef} />
      )}
    </>
  );
}
