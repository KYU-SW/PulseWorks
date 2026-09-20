import { useEffect, useRef } from "react";
import { MedicationDefinition } from "../../medications/types";
import { MEDICATION_SAFETY_NOTICE } from "../../medications/medicationGlossary";

interface MedicationDialogProps {
  medication: MedicationDefinition;
  // 다이얼로그가 실제로 닫혔을 때(close 이벤트) 호출된다 — 부모가 이
  // 콜백을 받아 자신의 open 상태를 내린다. 버튼 클릭이나 Esc가 직접
  // React 상태를 바꾸지 않고, 항상 네이티브 close 이벤트를 거친다.
  onClosed: () => void;
  returnFocusRef: React.RefObject<HTMLButtonElement>;
}

// Task 18의 MedicalTermDialog와 접근성 패턴(showModal, aria-labelledby,
// 명시적 닫기 버튼, Esc, 포커스 복귀)은 동일하지만, 데이터 구조(약물
// 정의)와 안전 안내 문구가 달라 억지로 재사용하지 않고 전용 컴포넌트로
// 둔다.
export default function MedicationDialog({ medication, onClosed, returnFocusRef }: MedicationDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const titleId = `medication-dialog-title-${medication.id}`;

  useEffect(() => {
    dialogRef.current?.showModal();
    // 실제 브라우저의 showModal() 자동 포커스 이동을 명시적으로
    // 보장한다 — Esc keydown이 dialog까지 버블링되려면 포커스가 dialog
    // 밖(원래 약물 버튼)에 남아있지 않아야 한다.
    closeButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;

    function handleClose() {
      onClosed();
      returnFocusRef.current?.focus();
    }

    dialog.addEventListener("close", handleClose);
    return () => dialog.removeEventListener("close", handleClose);
  }, [onClosed, returnFocusRef]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return undefined;

    // jsdom은 Esc의 네이티브 dialog 처리(cancel -> close)를 구현하지
    // 않으므로, 실제 브라우저와 테스트 환경 모두에서 동작하도록 Esc를
    // 직접 close()로 연결한다.
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        dialogRef.current?.close();
      }
    }

    dialog.addEventListener("keydown", handleKeyDown);
    return () => dialog.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <dialog ref={dialogRef} aria-labelledby={titleId}>
      <h2 id={titleId}>{medication.displayName}</h2>
      <p>{medication.plainDefinition}</p>
      {medication.caution && <p>{medication.caution}</p>}
      <p style={{ whiteSpace: "pre-line" }}>{MEDICATION_SAFETY_NOTICE}</p>
      <p>{medication.sourceLabel}</p>
      <button type="button" ref={closeButtonRef} onClick={() => dialogRef.current?.close()}>
        닫기
      </button>
    </dialog>
  );
}
