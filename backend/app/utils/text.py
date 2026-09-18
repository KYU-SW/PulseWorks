def truncate_for_display(text: str, limit: int = 300) -> str:
    """단순 표시용 길이 제한 — AI 요약이 아니다. 원문이 limit자 이하면
    그대로 반환하고, 넘으면 앞부분만 잘라 말줄임(...)을 붙인다.

    Task 8 타임라인(app/routers/encounters.py)과 Task 12 보고서 데이터
    수집 서비스(app/services/report_data.py)가 이 함수를 공유한다."""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."
