import json
from typing import Dict, Any

class ClinicalDocumentExporter:
    """Exports clinical documentation into various formats (JSON, Markdown, Formatted Text)."""

    @staticmethod
    def to_json(soap_data: Dict[str, Any], indent: int = 2) -> str:
        return json.dumps(soap_data, indent=indent)

    @staticmethod
    def to_markdown(soap_data: Dict[str, Any]) -> str:
        meta = soap_data.get("metadata", {})
        patient_header = ""
        if meta:
            patient_header = (
                f"**Patient**: {meta.get('name', 'N/A')} | "
                f"**Age/Gender**: {meta.get('age', 'N/A')} {meta.get('gender', '')} | "
                f"**MRN**: {meta.get('mrn', 'N/A')}\n\n---\n\n"
            )

        return (
            f"# CLINICAL ENCOUNTER SUMMARY\n\n"
            f"{patient_header}"
            f"## [S] Subjective\n{soap_data.get('subjective', '')}\n\n"
            f"## [O] Objective\n{soap_data.get('objective', '')}\n\n"
            f"## [A] Assessment\n{soap_data.get('assessment', '')}\n\n"
            f"## [P] Plan\n{soap_data.get('plan', '')}\n"
        )
