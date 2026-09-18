"""검사결과를 (검사명, 단위) 기준으로 그룹화하는 공용 로직.

GET /patients/{patient_id}/lab-trends(Task 11)와 report_data.
collect_report_data()(Task 12)가 이 모듈을 함께 재사용한다 — 그룹화·
정렬 로직을 두 곳에 따로 두지 않는다. DB에는 접근하지 않는다: 이미
조회된 LabResult 목록을 받아 순수하게 그룹화만 한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.models import LabResult
from app.services.safety_rules import evaluate_lab_abnormal


@dataclass(frozen=True)
class LabTrendPoint:
    value: float
    unit: str
    reference_low: float
    reference_high: float
    measured_at: datetime
    status: str
    rule_id: str
    encounter_id: int
    source_type: str


@dataclass(frozen=True)
class LabTrendGroup:
    test_name: str
    unit: str
    points: list[LabTrendPoint]


def group_lab_results_by_test(lab_results: list[LabResult]) -> list[LabTrendGroup]:
    """(test_name, unit) 기준으로 그룹화하고, 그룹 내부는 measured_at
    오름차순으로 정렬한다. 같은 검사명이라도 단위가 다르면 별도 그룹이다
    (서로 다른 단위를 한 그룹에 섞지 않는다). 각 점에는 Task 9
    evaluate_lab_abnormal()의 판정(status, rule_id)을 그대로 붙인다 —
    새로운 정상/이상 판정 로직을 만들지 않는다.

    그룹 순서는 (test_name, unit) 오름차순으로 결정적이다.
    """
    groups: dict[tuple[str, str], list[LabResult]] = {}
    for lab in lab_results:
        groups.setdefault((lab.test_name, lab.unit), []).append(lab)

    result: list[LabTrendGroup] = []
    for (test_name, unit), labs in sorted(groups.items(), key=lambda item: item[0]):
        points: list[LabTrendPoint] = []
        for lab in sorted(labs, key=lambda lab: lab.measured_at):
            judgment = evaluate_lab_abnormal(
                lab.value, lab.reference_low, lab.reference_high, lab.unit
            )
            points.append(
                LabTrendPoint(
                    value=lab.value,
                    unit=lab.unit,
                    reference_low=lab.reference_low,
                    reference_high=lab.reference_high,
                    measured_at=lab.measured_at,
                    status=judgment.status.value,
                    rule_id=judgment.rule_id,
                    encounter_id=lab.encounter_id,
                    source_type=lab.source_type.value,
                )
            )
        result.append(LabTrendGroup(test_name=test_name, unit=unit, points=points))
    return result
