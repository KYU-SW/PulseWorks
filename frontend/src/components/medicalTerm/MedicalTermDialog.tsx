import { useEffect, useRef } from "react";
import { MedicalTerm } from "../../medicalTerms/types";
import { MEDICAL_TERM_SAFETY_NOTICE } from "../../medicalTerms/glossary";

interface MedicalTermDialogProps {
  term: MedicalTerm;
  // 다이얼로그가 실제로 닫혔을 때(close 이벤트) 호출된다 — 부모가 이
  // 콜백을 받아 자신의 open 상태를 내린다. 버튼 클릭이나 Esc가 직접
  // React 상태를 바꾸지 않고, 항상 네이티브 close 이벤트를 거친다.
  onClosed: () => void;
  returnFocusRef: React.RefObject<HTMLButtonElement>;
}

export default function MedicalTermDialog({ term, onClosed, returnFocusRef }: MedicalTermDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const titleId = `medical-term-dialog-title-${term.id}`;

  useEffect(() => {
    dialogRef.current?.showModal();
    // 네이티브 showModal()은 실제 브라우저에서 다이얼로그 안의 첫 포커스
    // 가능한 요소로 포커스를 옮긴다. 명시적으로 닫기 버튼에 포커스를
    // 두어 이 동작을 보장한다 — Esc 키다운이 dialog까지 버블링되려면
    // 포커스가 dialog 밖(원래 용어 버튼)에 남아있지 않아야 한다.
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

    // 네이티브 <dialog>는 실제 브라우저에서 Esc를 자동으로 처리하지만,
    // 이 프로젝트의 테스트 환경(jsdom)은 그 키보드 동작을 구현하지
    // 않는다 — 두 환경 모두에서 동작하도록 Esc를 직접 close()로
    // 연결한다. 이미 닫힌 dialog에 close()를 다시 호출해도 아무 일도
    // 일어나지 않으므로(브라우저의 기본 Esc 처리와) 안전하게 공존한다.
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
      <h2 id={titleId}>{term.term}</h2>
      <p>{term.plainDefinition}</p>
      {term.caution && <p>{term.caution}</p>}
      <p style={{ whiteSpace: "pre-line" }}>{MEDICAL_TERM_SAFETY_NOTICE}</p>
      <p>{term.sourceLabel}</p>
      <button type="button" ref={closeButtonRef} onClick={() => dialogRef.current?.close()}>
        닫기
      </button>
    </dialog>
  );
}
