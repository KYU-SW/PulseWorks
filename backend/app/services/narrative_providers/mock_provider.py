from app.schemas.clinical_report import EmrSnapshot
from app.services.mock_narrative import generate_mock_report_narrative
from app.services.narrative_providers.base import NarrativeProvider, NarrativeProviderResult


class DeterministicMockProvider(NarrativeProvider):
    """기존 generate_mock_report_narrative()를 감싸기만 한다 - 그 함수는
    한 글자도 수정하지 않았고, summary_text와 source_record_ids를 그대로
    옮길 뿐 어떤 값도 바꾸지 않는다. NARRATIVE_PROVIDER=mock일 때 Task 16
    당시와 완전히 동일한 narrative/cited_record_ids가 나와야 한다."""

    def generate(self, snapshot: EmrSnapshot) -> NarrativeProviderResult:
        result = generate_mock_report_narrative(snapshot)
        return NarrativeProviderResult(
            narrative=result.summary_text,
            cited_record_ids=list(result.source_record_ids),
            mentioned_measurements=[],
            provider=result.provider,
            model="n/a",
            version=result.version,
        )
