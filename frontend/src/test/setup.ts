import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// jsdom (현재 버전 기준)은 HTMLDialogElement.showModal()/close()를
// 구현하지 않는다 — 실제 모달 동작 없이 HTMLElement를 그대로 상속만
// 하는 빈 구현이다. 이 프로젝트의 MedicalTermDialog(Task 18)처럼 네이티브
// <dialog>를 쓰는 컴포넌트를 테스트하려면 최소한의 계약(open 속성 반영,
// close 이벤트 발생)만 보강해 주면 된다. 실제 브라우저에 이미 구현이
// 있으면 절대 덮어쓰지 않는다.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
    this.setAttribute("open", "");
  };
}
if (!HTMLDialogElement.prototype.close) {
  HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
    if (!this.hasAttribute("open")) return;
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
}

afterEach(() => {
  cleanup();
  sessionStorage.clear();
});
