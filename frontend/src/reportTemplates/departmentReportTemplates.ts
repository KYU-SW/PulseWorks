import { DepartmentReportTemplate, ReportDepartment, ReportSectionConfig } from "./types";

// 섹션 제목과 빈 상태 정책의 단일 원본. 여기 없는 section id는 어떤
// 템플릿에도 나타날 수 없다(타입 레벨에서 강제).
const SECTION_DEFAULTS: Record<string, ReportSectionConfig> = {
  patient_info: { id: "patient_info", title: "환자 기본정보", emptyBehavior: "show_empty_state" },
  selected_encounter: {
    id: "selected_encounter", title: "선택 Encounter", emptyBehavior: "show_empty_state",
  },
  vital_signs: { id: "vital_signs", title: "활력징후", emptyBehavior: "hide" },
  diagnoses: { id: "diagnoses", title: "주요 진단", emptyBehavior: "hide" },
  lab_trends: { id: "lab_trends", title: "검사 추세", emptyBehavior: "hide" },
  lab_results: { id: "lab_results", title: "검사결과", emptyBehavior: "hide" },
  prescriptions: { id: "prescriptions", title: "처방 기록", emptyBehavior: "hide" },
  allergies: { id: "allergies", title: "알레르기", emptyBehavior: "show_empty_state" },
  safety_alerts: { id: "safety_alerts", title: "안전 알림", emptyBehavior: "show_empty_state" },
  clinical_notes: { id: "clinical_notes", title: "진료기록 미리보기", emptyBehavior: "hide" },
  source_record_ids: { id: "source_record_ids", title: "근거 기록", emptyBehavior: "hide" },
};

function sections(...ids: (keyof typeof SECTION_DEFAULTS)[]): ReportSectionConfig[] {
  return ids.map((id) => SECTION_DEFAULTS[id]);
}

export const DEPARTMENT_REPORT_TEMPLATES: Record<ReportDepartment, DepartmentReportTemplate> = {
  ENDOCRINOLOGY: {
    department: "ENDOCRINOLOGY",
    sections: sections(
      "patient_info", "diagnoses", "lab_trends", "lab_results", "selected_encounter",
      "vital_signs", "prescriptions", "allergies", "safety_alerts", "clinical_notes",
      "source_record_ids"
    ),
  },
  ORTHOPEDICS: {
    department: "ORTHOPEDICS",
    sections: sections(
      "patient_info", "diagnoses", "selected_encounter", "vital_signs", "prescriptions",
      "clinical_notes", "lab_results", "allergies", "safety_alerts", "source_record_ids"
    ),
  },
  EMERGENCY_MEDICINE: {
    department: "EMERGENCY_MEDICINE",
    sections: sections(
      "patient_info", "selected_encounter", "vital_signs", "diagnoses", "lab_results",
      "prescriptions", "allergies", "safety_alerts", "clinical_notes", "source_record_ids"
    ),
  },
  DEFAULT: {
    department: "DEFAULT",
    sections: sections(
      "patient_info", "selected_encounter", "vital_signs", "diagnoses", "lab_results",
      "lab_trends", "prescriptions", "allergies", "safety_alerts", "clinical_notes",
      "source_record_ids"
    ),
  },
};

const KNOWN_DEPARTMENTS = new Set<string>(["ENDOCRINOLOGY", "ORTHOPEDICS", "EMERGENCY_MEDICINE"]);

/**
 * 순수 함수 — Encounter들의 department 문자열 목록에서 보고서 템플릿을
 * 고른다. 알려진 진료과가 정확히 하나로 모이면 그 템플릿, 그 외(없음/
 * 알 수 없음/서로 다른 진료과가 둘 이상)는 항상 DEFAULT. 같은 진료과가
 * 여러 Encounter에 반복돼도 집합 기준으로 하나면 그 템플릿을 그대로
 * 쓴다. 백엔드에 진료과 판정용 필드를 새로 요청하지 않는다 — 이미
 * content.emr_snapshot.encounters[].department에 있는 값만 사용한다.
 */
export function selectReportTemplate(departments: string[]): DepartmentReportTemplate {
  const unique = new Set(departments);
  if (unique.size === 1) {
    const [only] = unique;
    if (KNOWN_DEPARTMENTS.has(only)) {
      return DEPARTMENT_REPORT_TEMPLATES[only as ReportDepartment];
    }
  }
  return DEPARTMENT_REPORT_TEMPLATES.DEFAULT;
}
