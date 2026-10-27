"""Template validation and template-value leakage checks (DB-031, DB-033 template rules).

Templates supply layout, never facts. A template is usable only after it is validated against
reviewed structural requirements, and its illustrative values (``0 PSI``, ``5°C/min``) must never
appear in site output unless independent site evidence supports them.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict

from .parsing import OperationalDocument, lookup_key


class TemplateRequirements(BaseModel):
    """Reviewed expectations for a template kind. Comes from reviewers, not from the template itself."""

    model_config = ConfigDict(frozen=True)

    template_kind: str
    required_sections: tuple[str, ...]
    reviewed_by: str
    reviewed_on: date


class TemplateProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_id: str
    content_sha256: str
    section_titles: tuple[str, ...]
    illustrative_values: frozenset[str]  # normalized quantity strings found in the template
    placeholders: tuple[str, ...]


class TemplateValidation(BaseModel):
    valid: bool
    problems: list[str]
    profile: TemplateProfile


def build_template_profile(doc: OperationalDocument) -> TemplateProfile:
    return TemplateProfile(
        artifact_id=doc.artifact_id,
        content_sha256=doc.text_sha256,
        section_titles=tuple(s.title for s in doc.sections),
        illustrative_values=frozenset(v.normalized for v in doc.stated_values),
        placeholders=tuple(f.text for f in doc.findings if f.code == "template_placeholder"),
    )


def _section_key(title: str) -> str:
    # "## 3. Step-by-Step Procedure" and "Step-by-step procedure" compare equal.
    key = lookup_key(title)
    return key.split(". ", 1)[1] if key[:1].isdigit() and ". " in key else key


def validate_template(doc: OperationalDocument, requirements: TemplateRequirements) -> TemplateValidation:
    profile = build_template_profile(doc)
    problems: list[str] = []
    if doc.findings_of("empty_document"):
        problems.append("template is empty")
    present = {_section_key(t) for t in profile.section_titles}
    for required in requirements.required_sections:
        if _section_key(required) not in present:
            problems.append(f"missing required section {required!r}")
    for finding in doc.findings_of("missing_reference"):
        problems.append(f"broken reference {finding.text}")
    return TemplateValidation(valid=not problems, problems=problems, profile=profile)


class LeakageFinding(BaseModel):
    value: str
    line: int
    message: str


def find_template_leakage(
    draft: OperationalDocument, template: TemplateProfile, supported_values: frozenset[str] = frozenset()
) -> list[LeakageFinding]:
    """Template example values that reappear in a site document without supporting site evidence."""
    findings: list[LeakageFinding] = []
    for value in draft.stated_values:
        if value.normalized in template.illustrative_values and value.normalized not in supported_values:
            findings.append(
                LeakageFinding(
                    value=value.text,
                    line=value.span.line_start,
                    message="value matches a template example and has no supporting site evidence",
                )
            )
    return findings
