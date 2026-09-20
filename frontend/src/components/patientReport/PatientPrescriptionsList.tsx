import { PatientPrescription } from "../../api/patientReports";
import { findMedication } from "../../medications/findMedication";
import MedicationButton from "../medication/MedicationButton";
import { formatDateTime } from "../labTrend/LabTrendPresentation";
import { formatPatientDosage } from "./formatPatientDosage";

// "Task10VerifyNonConflictMedX"는 실제 약물명이 아니라 개발 검증용
// 합성 문자열이다(Task 9/10 안전 규칙 검증에 쓰인 값). 정확히 이
// 문자열일 때만 투명한 안내로 바꾼다 — 일반적인 약물명 추정 규칙이
// 아니며, 저장된 medication_name/스냅샷 자체는 바꾸지 않고 이 표시
// 컴포넌트 안에서만 변환한다.
const DEV_TEST_MEDICATION_NAME = "Task10VerifyNonConflictMedX";
const DEV_TEST_MEDICATION_DISPLAY_LABEL = "합성 테스트 약물(개발 검증용)";

export default function PatientPrescriptionsList({
  prescriptions,
}: {
  prescriptions: PatientPrescription[];
}) {
  if (prescriptions.length === 0) return null;

  return (
    <ul>
      {prescriptions.map((prescription, index) => {
        const isDevTestMedication = prescription.medication_name === DEV_TEST_MEDICATION_NAME;
        const medication = isDevTestMedication ? null : findMedication(prescription.medication_name);

        return (
          <li key={`${prescription.prescribed_at}-${index}`}>
            {isDevTestMedication ? (
              <span>{DEV_TEST_MEDICATION_DISPLAY_LABEL}</span>
            ) : medication ? (
              <MedicationButton medication={medication}>{medication.displayName}</MedicationButton>
            ) : (
              <span>{prescription.medication_name}</span>
            )}
            {" — "}
            {formatPatientDosage(prescription.dosage)}
            {" — "}
            {formatDateTime(prescription.prescribed_at)}
          </li>
        );
      })}
    </ul>
  );
}
