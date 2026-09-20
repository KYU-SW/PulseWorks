// 환자용 표시에서만 쓰는 용량 문자열 정리 — 숫자나 단위 자체를
// 바꾸지 않는다(환산·반올림 없음), 복용 횟수·투여 경로를 추정하지
// 않는다. 인식하지 못하는 형식은 원문 그대로 돌려준다.
//
// "500mg" -> "500 mg" (숫자와 단위 사이 공백만 추가)
// "1 tablet" -> "1정", "2 tablets" -> "2정" (일반적인 "{숫자} tablet(s)" 형식)
export function formatPatientDosage(rawDosage: string): string {
  const trimmed = rawDosage.trim();

  const mgMatch = trimmed.match(/^(\d+(?:\.\d+)?)\s*mg$/i);
  if (mgMatch) {
    return `${mgMatch[1]} mg`;
  }

  const tabletMatch = trimmed.match(/^(\d+(?:\.\d+)?)\s*tablets?$/i);
  if (tabletMatch) {
    return `${tabletMatch[1]}정`;
  }

  return rawDosage;
}
