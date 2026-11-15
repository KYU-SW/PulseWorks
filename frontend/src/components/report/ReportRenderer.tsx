import { ReportContentSnapshot } from "../../api/clinicalReports";
import { selectReportTemplate } from "../../reportTemplates/departmentReportTemplates";
import { ReportSectionId } from "../../reportTemplates/types";
import { SectionComponentProps } from "./sectionProps";
import AllergiesSection from "./sections/AllergiesSection";
import ClinicalNotesSection from "./sections/ClinicalNotesSection";
import DiagnosesSection from "./sections/DiagnosesSection";
import EvidenceSection from "./sections/EvidenceSection";
import LabResultsTableSection from "./sections/LabResultsTableSection";
import LabTrendsSection from "./sections/LabTrendsSection";
import PatientInfoSection from "./sections/PatientInfoSection";
import PrescriptionsSection from "./sections/PrescriptionsSection";
import SafetyAlertsSection from "./sections/SafetyAlertsSection";
import SelectedEncounterSection from "./sections/SelectedEncounterSection";
import VitalSignsSection from "./sections/VitalSignsSection";

// section id와 React 컴포넌트의 유일한 연결점. 새 진료과가 생겨도 이
// 매핑은 그대로이고 departmentReportTemplates.ts에 설정만 추가하면
// 된다 — 진료과별로 별도 컴포넌트를 복제하지 않는다.
const SECTION_COMPONENTS: Record<ReportSectionId, React.ComponentType<SectionComponentProps>> = {
  patient_info: PatientInfoSection,
  selected_encounter: SelectedEncounterSection,
  vital_signs: VitalSignsSection,
  diagnoses: DiagnosesSection,
  lab_trends: LabTrendsSection,
  lab_results: LabResultsTableSection,
  prescriptions: PrescriptionsSection,
  allergies: AllergiesSection,
  safety_alerts: SafetyAlertsSection,
  clinical_notes: ClinicalNotesSection,
  source_record_ids: EvidenceSection,
};

/**
 * 저장된 ClinicalReport.content 스냅샷을 진료과 설정에 따라 렌더링하는
 * 공통 컴포넌트. 데이터 fetch/API 호출/서버 쓰기/content 수정/권한
 * 판단/상태 전이/AI 설명 생성을 전혀 하지 않는 상태 없는 프레젠테이션
 * 컴포넌트다 — 그런 로직은 여기 절대 추가하지 않는다.
 */
export default function ReportRenderer({ content }: { content: ReportContentSnapshot }) {
  const { emr_snapshot: snapshot } = content;
  const departments = snapshot.encounters.map((encounter) => encounter.department);
  const template = selectReportTemplate(departments);

  return (
    <div>
      {template.sections.map((section) => {
        const SectionComponent = SECTION_COMPONENTS[section.id];
        return (
          <SectionComponent
            key={section.id}
            snapshot={snapshot}
            title={section.title}
            emptyBehavior={section.emptyBehavior}
          />
        );
      })}
    </div>
  );
}
