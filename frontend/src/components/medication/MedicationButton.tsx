import { useRef, useState } from "react";
import { MedicationDefinition } from "../../medications/types";
import MedicationDialog from "./MedicationDialog";

interface MedicationButtonProps {
  medication: MedicationDefinition;
  children: React.ReactNode;
}

// 실제 button 요소이므로 Tab 이동, Enter/Space 활성화가 브라우저 기본
// 동작으로 자연히 충족된다. 밑줄과 ⓘ 아이콘으로 색상과 무관하게 클릭
// 가능함을 알리고, hover만으로는 열리지 않는다.
export default function MedicationButton({ medication, children }: MedicationButtonProps) {
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
        <MedicationDialog
          medication={medication}
          onClosed={() => setOpen(false)}
          returnFocusRef={triggerRef}
        />
      )}
    </>
  );
}
